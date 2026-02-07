import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Count, Q
from django.http import JsonResponse
from .models import Play, PlaySession, Rating, Report
import json
from datetime import datetime

# ============= HELPER FUNCTIONS =============

def get_flask_api(endpoint):
    """Make GET request to Flask API"""
    try:
        response = requests.get(f"{settings.FLASK_API_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Flask API Error: {e}")
        return None

def post_flask_api(endpoint, data):
    """Make POST request to Flask API"""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            f"{settings.FLASK_API_URL}{endpoint}",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Flask API Error: {e}")
        return None

def put_flask_api(endpoint, data):
    """Make PUT request to Flask API"""
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.put(
            f"{settings.FLASK_API_URL}{endpoint}",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Flask API Error: {e}")
        return None

def delete_flask_api(endpoint):
    """Make DELETE request to Flask API"""
    try:
        response = requests.delete(f"{settings.FLASK_API_URL}{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Flask API Error: {e}")
        return None

def is_author(user):
    """Check if user is an author (Level 16)"""
    return user.groups.filter(name='Author').exists() or user.is_staff

def is_admin(user):
    """Check if user is an admin"""
    return user.is_staff

# ============= PUBLIC VIEWS (LEVEL 10) =============

def story_list(request):
    """Display list of published stories"""
    stories = get_flask_api('/stories?status=published')
    
    if stories is None:
        messages.error(request, 'Could not connect to story service')
        stories = []
    
    # Level 18: Add ratings info
    for story in stories:
        ratings = Rating.objects.filter(story_id=story['id'])
        if ratings.exists():
            story['avg_rating'] = sum(r.score for r in ratings) / len(ratings)
            story['rating_count'] = len(ratings)
        else:
            story['avg_rating'] = 0
            story['rating_count'] = 0
    
    context = {
        'stories': stories,
        'page_title': 'All Stories'
    }
    return render(request, 'stories/story_list.html', context)


def story_detail(request, story_id):
    """Display story details"""
    story = get_flask_api(f'/stories/{story_id}')
    
    if not story:
        messages.error(request, 'Story not found')
        return redirect('stories:story_list')
    
    # Get statistics
    plays = Play.objects.filter(story_id=story_id)
    total_plays = plays.count()
    
    # Ending distribution
    ending_stats = plays.values('ending_page_id').annotate(count=Count('ending_page_id'))
    
    # Get all pages to show ending labels
    tree_data = get_flask_api(f'/stories/{story_id}/tree')
    endings = {}
    if tree_data:
        for page in tree_data.get('pages', []):
            if page.get('is_ending'):
                endings[page['id']] = page.get('ending_label', f"Ending {page['id']}")
    
    # Calculate percentages
    ending_distribution = []
    for stat in ending_stats:
        ending_id = stat['ending_page_id']
        count = stat['count']
        percentage = (count / total_plays * 100) if total_plays > 0 else 0
        ending_distribution.append({
            'ending_id': ending_id,
            'ending_label': endings.get(ending_id, f'Ending {ending_id}'),
            'count': count,
            'percentage': round(percentage, 1)
        })
    
    # Level 18: Ratings and comments
    ratings = Rating.objects.filter(story_id=story_id).select_related('user')
    avg_rating = sum(r.score for r in ratings) / len(ratings) if ratings else 0
    user_rating = None
    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(story_id=story_id, user=request.user)
        except Rating.DoesNotExist:
            pass
    
    context = {
        'story': story,
        'total_plays': total_plays,
        'ending_distribution': ending_distribution,
        'ratings': ratings,
        'avg_rating': round(avg_rating, 1),
        'rating_count': len(ratings),
        'user_rating': user_rating,
    }
    return render(request, 'stories/story_detail.html', context)


def play_story(request, story_id):
    """Start playing a story"""
    story = get_flask_api(f'/stories/{story_id}')
    
    if not story:
        messages.error(request, 'Story not found')
        return redirect('stories:story_list')
    
    # Check if story is suspended (Level 16)
    if story.get('status') == 'suspended':
        messages.error(request, 'This story is currently unavailable')
        return redirect('stories:story_list')
    
    # Get or create session for auto-save (Level 13)
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    
    # Get start page
    start_page = get_flask_api(f'/stories/{story_id}/start')
    
    if not start_page:
        messages.error(request, 'Story has no starting page')
        return redirect('stories:story_detail', story_id=story_id)
    
    # Create or update play session (Level 13)
    play_session, created = PlaySession.objects.get_or_create(
        session_key=session_key,
        story_id=story_id,
        defaults={
            'current_page_id': start_page['id'],
            'path_history': [start_page['id']],
            'user': request.user if request.user.is_authenticated else None
        }
    )
    
    if not created:
        # Reset session for new playthrough
        play_session.current_page_id = start_page['id']
        play_session.path_history = [start_page['id']]
        play_session.save()
    
    return redirect('stories:play_page', story_id=story_id, page_id=start_page['id'])


def play_page(request, story_id, page_id):
    """Display a story page during gameplay"""
    story = get_flask_api(f'/stories/{story_id}')
    page = get_flask_api(f'/pages/{page_id}')
    
    if not story or not page:
        messages.error(request, 'Page not found')
        return redirect('stories:story_list')
    
    # Update play session (Level 13)
    session_key = request.session.session_key
    if session_key:
        try:
            play_session = PlaySession.objects.get(session_key=session_key, story_id=story_id)
            play_session.current_page_id = page_id
            if page_id not in play_session.path_history:
                play_session.path_history.append(page_id)
            play_session.save()
        except PlaySession.DoesNotExist:
            pass
    
    # Check if this is an ending
    if page.get('is_ending'):
        # Record the play
        Play.objects.create(
            story_id=story_id,
            ending_page_id=page_id,
            user=request.user if request.user.is_authenticated else None
        )
        
        context = {
            'story': story,
            'page': page,
            'is_ending': True,
            'ending_label': page.get('ending_label', 'The End')
        }
        return render(request, 'stories/play_ending.html', context)
    
    # Level 18: Handle dice rolls for choices
    choices = page.get('choices', [])
    for choice in choices:
        if choice.get('requires_dice_roll'):
            # This will be handled in the template with JavaScript
            choice['needs_roll'] = True
    
    context = {
        'story': story,
        'page': page,
        'choices': choices,
        'is_ending': False
    }
    return render(request, 'stories/play_page.html', context)


def statistics(request):
    """Display global statistics"""
    stories = get_flask_api('/stories?status=published') or []
    
    stats = []
    for story in stories:
        plays = Play.objects.filter(story_id=story['id'])
        total_plays = plays.count()
        
        # Get ending distribution
        ending_counts = plays.values('ending_page_id').annotate(count=Count('ending_page_id'))
        
        stats.append({
            'story': story,
            'total_plays': total_plays,
            'unique_endings': ending_counts.count(),
            'ending_counts': list(ending_counts)
        })
    
    context = {
        'stats': stats,
        'total_plays_all': sum(s['total_plays'] for s in stats)
    }
    return render(request, 'stories/statistics.html', context)


# ============= AUTHOR VIEWS (LEVEL 10 - Open, LEVEL 16 - Protected) =============

def create_story(request):
    """Create a new story"""
    # Level 16: Require authentication and author role
    # For Level 10, this is open to all
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        status = request.POST.get('status', 'published')
        
        data = {
            'title': title,
            'description': description,
            'status': status,
            'author_id': request.user.id if request.user.is_authenticated else None
        }
        
        story = post_flask_api('/stories', data)
        
        if story:
            messages.success(request, f'Story "{title}" created successfully!')
            return redirect('stories:edit_story', story_id=story['id'])
        else:
            messages.error(request, 'Failed to create story')
    
    return render(request, 'stories/create_story.html')


def edit_story(request, story_id):
    """Edit an existing story"""
    story = get_flask_api(f'/stories/{story_id}')
    
    if not story:
        messages.error(request, 'Story not found')
        return redirect('stories:story_list')
    
    # Level 16: Check ownership
    # For Level 10, editing is open to all
    
    if request.method == 'POST':
        data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description'),
            'status': request.POST.get('status'),
            'illustration': request.POST.get('illustration', '')
        }
        
        updated_story = put_flask_api(f'/stories/{story_id}', data)
        
        if updated_story:
            messages.success(request, 'Story updated successfully!')
            return redirect('stories:edit_story', story_id=story_id)
        else:
            messages.error(request, 'Failed to update story')
    
    # Get all pages for this story
    tree_data = get_flask_api(f'/stories/{story_id}/tree')
    pages = tree_data.get('pages', []) if tree_data else []
    
    context = {
        'story': story,
        'pages': pages
    }
    return render(request, 'stories/edit_story.html', context)


def delete_story(request, story_id):
    """Delete a story"""
    if request.method == 'POST':
        result = delete_flask_api(f'/stories/{story_id}')
        
        if result:
            messages.success(request, 'Story deleted successfully')
            return redirect('stories:story_list')
        else:
            messages.error(request, 'Failed to delete story')
    
    return redirect('stories:edit_story', story_id=story_id)


def add_page(request, story_id):
    """Add a new page to a story"""
    if request.method == 'POST':
        data = {
            'text': request.POST.get('text'),
            'is_ending': request.POST.get('is_ending') == 'on',
            'ending_label': request.POST.get('ending_label', ''),
            'illustration': request.POST.get('illustration', '')
        }
        
        page = post_flask_api(f'/stories/{story_id}/pages', data)
        
        if page:
            messages.success(request, 'Page added successfully!')
        else:
            messages.error(request, 'Failed to add page')
    
    return redirect('stories:edit_story', story_id=story_id)


def edit_page(request, page_id):
    """Edit a page"""
    page = get_flask_api(f'/pages/{page_id}')
    
    if not page:
        messages.error(request, 'Page not found')
        return redirect('stories:story_list')
    
    if request.method == 'POST':
        data = {
            'text': request.POST.get('text'),
            'is_ending': request.POST.get('is_ending') == 'on',
            'ending_label': request.POST.get('ending_label', ''),
            'illustration': request.POST.get('illustration', '')
        }
        
        updated_page = put_flask_api(f'/pages/{page_id}', data)
        
        if updated_page:
            messages.success(request, 'Page updated successfully!')
            return redirect('stories:edit_story', story_id=page['story_id'])
        else:
            messages.error(request, 'Failed to update page')
    
    context = {'page': page}
    return render(request, 'stories/edit_page.html', context)


def delete_page(request, page_id):
    """Delete a page"""
    if request.method == 'POST':
        page = get_flask_api(f'/pages/{page_id}')
        story_id = page['story_id'] if page else None
        
        result = delete_flask_api(f'/pages/{page_id}')
        
        if result:
            messages.success(request, 'Page deleted successfully')
        else:
            messages.error(request, 'Failed to delete page')
        
        if story_id:
            return redirect('stories:edit_story', story_id=story_id)
    
    return redirect('stories:story_list')


def add_choice(request, page_id):
    """Add a choice to a page"""
    if request.method == 'POST':
        data = {
            'text': request.POST.get('text'),
            'next_page_id': int(request.POST.get('next_page_id')),
            'requires_dice_roll': request.POST.get('requires_dice_roll') == 'on',
            'dice_threshold': int(request.POST.get('dice_threshold', 0)) if request.POST.get('dice_threshold') else None
        }
        
        choice = post_flask_api(f'/pages/{page_id}/choices', data)
        
        if choice:
            messages.success(request, 'Choice added successfully!')
        else:
            messages.error(request, 'Failed to add choice')
        
        # Get page to find story_id
        page = get_flask_api(f'/pages/{page_id}')
        if page:
            return redirect('stories:edit_story', story_id=page['story_id'])
    
    return redirect('stories:story_list')


def edit_choice(request, choice_id):
    """Edit a choice"""
    # This would require getting choice details first
    # Simplified for now - redirect to story edit
    return redirect('stories:story_list')


def delete_choice(request, choice_id):
    """Delete a choice"""
    if request.method == 'POST':
        result = delete_flask_api(f'/choices/{choice_id}')
        
        if result:
            messages.success(request, 'Choice deleted successfully')
        else:
            messages.error(request, 'Failed to delete choice')
    
    return redirect('stories:story_list')


# ============= LEVEL 13: SEARCH & PREVIEW =============

def search_stories(request):
    """Search and filter stories"""
    query = request.GET.get('q', '')
    
    # Get all published stories
    stories = get_flask_api('/stories?status=published') or []
    
    # Filter by search query
    if query:
        stories = [s for s in stories if query.lower() in s['title'].lower() or 
                   (s.get('description') and query.lower() in s['description'].lower())]
    
    # Add rating info (Level 18)
    for story in stories:
        ratings = Rating.objects.filter(story_id=story['id'])
        if ratings.exists():
            story['avg_rating'] = sum(r.score for r in ratings) / len(ratings)
            story['rating_count'] = len(ratings)
        else:
            story['avg_rating'] = 0
            story['rating_count'] = 0
    
    context = {
        'stories': stories,
        'query': query,
        'page_title': f'Search Results: {query}' if query else 'Search Stories'
    }
    return render(request, 'stories/story_list.html', context)


def preview_story(request, story_id):
    """Preview a draft story without recording statistics"""
    story = get_flask_api(f'/stories/{story_id}')
    
    if not story:
        messages.error(request, 'Story not found')
        return redirect('stories:story_list')
    
    # Get start page
    start_page = get_flask_api(f'/stories/{story_id}/start')
    
    if not start_page:
        messages.error(request, 'Story has no starting page')
        return redirect('stories:edit_story', story_id=story_id)
    
    # Similar to play_page but with preview flag
    context = {
        'story': story,
        'page': start_page,
        'choices': start_page.get('choices', []),
        'is_preview': True
    }
    return render(request, 'stories/play_page.html', context)


# ============= LEVEL 16: AUTHENTICATION =============

def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Default role is Reader (no group assignment needed)
            login(request, user)
            messages.success(request, 'Registration successful! You are now logged in.')
            return redirect('stories:story_list')
    else:
        form = UserCreationForm()
    
    return render(request, 'stories/register.html', {'form': form})


def user_login(request):
    """User login"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('stories:story_list')
    else:
        form = AuthenticationForm()
    
    return render(request, 'stories/login.html', {'form': form})


def user_logout(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('stories:story_list')


@login_required
def my_stories(request):
    """View user's own stories (Level 16)"""
    all_stories = get_flask_api('/stories') or []
    my_stories = [s for s in all_stories if s.get('author_id') == request.user.id]
    
    context = {
        'stories': my_stories,
        'page_title': 'My Stories'
    }
    return render(request, 'stories/story_list.html', context)


@login_required
def my_history(request):
    """View user's play history (Level 16)"""
    plays = Play.objects.filter(user=request.user).order_by('-created_at')
    
    # Enrich with story data
    play_data = []
    for play in plays:
        story = get_flask_api(f'/stories/{play.story_id}')
        page = get_flask_api(f'/pages/{play.ending_page_id}')
        
        play_data.append({
            'play': play,
            'story': story,
            'ending_label': page.get('ending_label', 'The End') if page else 'Unknown'
        })
    
    context = {'play_data': play_data}
    return render(request, 'stories/my_history.html', context)


# ============= LEVEL 16: ADMIN MODERATION =============

@user_passes_test(is_admin)
def moderate_stories(request):
    """Admin page to view and moderate all stories"""
    stories = get_flask_api('/stories') or []
    
    context = {
        'stories': stories,
        'page_title': 'Moderate Stories'
    }
    return render(request, 'stories/moderate_stories.html', context)


@user_passes_test(is_admin)
def suspend_story(request, story_id):
    """Suspend or unsuspend a story"""
    if request.method == 'POST':
        action = request.POST.get('action')
        new_status = 'suspended' if action == 'suspend' else 'published'
        
        data = {'status': new_status}
        result = put_flask_api(f'/stories/{story_id}', data)
        
        if result:
            messages.success(request, f'Story {action}ed successfully')
        else:
            messages.error(request, f'Failed to {action} story')
    
    return redirect('stories:moderate_stories')


# ============= LEVEL 18: COMMUNITY FEATURES =============

@login_required
def rate_story(request, story_id):
    """Rate a story"""
    if request.method == 'POST':
        score = int(request.POST.get('score'))
        comment = request.POST.get('comment', '')
        
        rating, created = Rating.objects.update_or_create(
            story_id=story_id,
            user=request.user,
            defaults={'score': score, 'comment': comment}
        )
        
        action = 'added' if created else 'updated'
        messages.success(request, f'Rating {action} successfully!')
    
    return redirect('stories:story_detail', story_id=story_id)


@login_required
def report_story(request, story_id):
    """Report a story"""
    if request.method == 'POST':
        reason = request.POST.get('reason')
        description = request.POST.get('description')
        
        Report.objects.create(
            story_id=story_id,
            user=request.user,
            reason=reason,
            description=description
        )
        
        messages.success(request, 'Report submitted. Thank you for helping keep the community safe.')
    
    return redirect('stories:story_detail', story_id=story_id)


@user_passes_test(is_admin)
def view_reports(request):
    """View all reports (admin only)"""
    reports = Report.objects.filter(is_resolved=False).order_by('-created_at')
    
    # Enrich with story data
    report_data = []
    for report in reports:
        story = get_flask_api(f'/stories/{report.story_id}')
        report_data.append({
            'report': report,
            'story': story
        })
    
    context = {'report_data': report_data}
    return render(request, 'stories/reports.html', context)


@user_passes_test(is_admin)
def resolve_report(request, report_id):
    """Resolve a report"""
    if request.method == 'POST':
        report = get_object_or_404(Report, id=report_id)
        report.is_resolved = True
        report.resolved_at = datetime.now()
        report.resolved_by = request.user
        report.save()
        
        messages.success(request, 'Report resolved')
    
    return redirect('stories:view_reports')


# ============= LEVEL 18: VISUALIZATIONS =============

def story_tree(request, story_id):
    """Visualize story structure as a tree"""
    story = get_flask_api(f'/stories/{story_id}')
    tree_data = get_flask_api(f'/stories/{story_id}/tree')
    
    if not story or not tree_data:
        messages.error(request, 'Story not found')
        return redirect('stories:story_list')
    
    context = {
        'story': story,
        'tree_data': json.dumps(tree_data)
    }
    return render(request, 'stories/story_tree.html', context)


@login_required
def play_history(request, play_id):
    """Visualize the path taken in a specific playthrough"""
    play = get_object_or_404(Play, id=play_id, user=request.user)
    
    # Get play session to retrieve path history
    try:
        session = PlaySession.objects.filter(
            user=request.user,
            story_id=play.story_id
        ).latest('updated_at')
        path_history = session.path_history
    except PlaySession.DoesNotExist:
        path_history = [play.ending_page_id]
    
    # Get story tree
    tree_data = get_flask_api(f'/stories/{play.story_id}/tree')
    
    context = {
        'play': play,
        'path_history': path_history,
        'tree_data': json.dumps(tree_data) if tree_data else '{}'
    }
    return render(request, 'stories/play_history.html', context)