import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib import messages
from .models import Play, PlaySession
from django.db.models import Count


FLASK_API = settings.FLASK_API_URL

def get_headers():
    """Level 16: Include API key for write operations"""
    return {'X-API-KEY': settings.FLASK_API_KEY}

# ============ PUBLIC STORY BROWSING ============

def story_list(request):
    """List all published stories"""
    try:
        response = requests.get(f"{FLASK_API}/stories?status=published")
        stories = response.json() if response.status_code == 200 else []
    except:
        stories = []
        messages.error(request, "Could not connect to story database")
    
    return render(request, 'stories/list.html', {'stories': stories})

def story_detail(request, story_id):
    """View story details"""
    try:
        response = requests.get(f"{FLASK_API}/stories/{story_id}")
        story = response.json() if response.status_code == 200 else None
    except:
        story = None
        messages.error(request, "Could not load story")
    
    # Get statistics
    plays = Play.objects.filter(story_id=story_id)
    total_plays = plays.count()
    endings_stats = plays.values('ending_page_id').annotate(count=Count('ending_page_id'))
    
    context = {
        'story': story,
        'total_plays': total_plays,
        'endings_stats': endings_stats
    }
    return render(request, 'stories/detail.html', context)

# ============ PLAYING STORIES ============

def play_story(request, story_id):
    """Start playing a story"""
    try:
        response = requests.get(f"{FLASK_API}/stories/{story_id}/start")
        if response.status_code == 200:
            page = response.json()
            return render(request, 'play/page.html', {
                'story_id': story_id,
                'page': page
            })
    except:
        messages.error(request, "Could not start story")
    
    return redirect('story_list')

def play_page(request, story_id, page_id):
    """Display a specific page during play"""
    try:
        response = requests.get(f"{FLASK_API}/pages/{page_id}")
        if response.status_code == 200:
            page = response.json()
            
            # If this is an ending, save the play
            if page.get('is_ending'):
                Play.objects.create(
                    story_id=story_id,
                    ending_page_id=page_id
                )
            
            return render(request, 'play/page.html', {
                'story_id': story_id,
                'page': page
            })
    except:
        messages.error(request, "Could not load page")
    
    return redirect('story_list')

# ============ STATISTICS ============

def statistics(request):
    """Show statistics for all stories"""
    # Get all plays grouped by story
    story_stats = Play.objects.values('story_id').annotate(
        play_count=Count('id')
    ).order_by('-play_count')
    
    # Get story details from Flask
    stories_data = []
    for stat in story_stats:
        try:
            response = requests.get(f"{FLASK_API}/stories/{stat['story_id']}")
            if response.status_code == 200:
                story = response.json()
                story['play_count'] = stat['play_count']
                
                # Get ending distribution
                endings = Play.objects.filter(
                    story_id=stat['story_id']
                ).values('ending_page_id').annotate(count=Count('id'))
                
                story['endings'] = []
                for ending in endings:
                    percentage = (ending['count'] / stat['play_count']) * 100
                    story['endings'].append({
                        'page_id': ending['ending_page_id'],
                        'count': ending['count'],
                        'percentage': round(percentage, 1)
                    })
                
                stories_data.append(story)
        except:
            pass
    
    return render(request, 'stories/statistics.html', {'stories': stories_data})

# ============ AUTHOR TOOLS (Level 10: No authentication) ============

def author_dashboard(request):
    """Author dashboard - list all stories"""
    try:
        response = requests.get(f"{FLASK_API}/stories?status=published")
        stories = response.json() if response.status_code == 200 else []
    except:
        stories = []
    
    return render(request, 'author/dashboard.html', {'stories': stories})

def story_create(request):
    """Create a new story"""
    if request.method == 'POST':
        data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description'),
            'status': 'published'
        }
        try:
            response = requests.post(f"{FLASK_API}/stories", json=data)
            if response.status_code == 201:
                story = response.json()
                messages.success(request, 'Story created successfully!')
                return redirect('story_edit', story_id=story['id'])
        except:
            messages.error(request, 'Could not create story')
    
    return render(request, 'author/story_form.html')

def story_edit(request, story_id):
    """Edit a story and manage pages/choices"""
    try:
        response = requests.get(f"{FLASK_API}/stories/{story_id}")
        story = response.json() if response.status_code == 200 else None
        
        if not story:
            messages.error(request, 'Story not found')
            return redirect('author_dashboard')
        
        # Get all pages for this story
        # We'll need to add an endpoint or filter
        
    except:
        messages.error(request, 'Could not load story')
        return redirect('author_dashboard')
    
    if request.method == 'POST':
        # Update story
        data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description')
        }
        try:
            response = requests.put(f"{FLASK_API}/stories/{story_id}", json=data)
            if response.status_code == 200:
                messages.success(request, 'Story updated!')
                return redirect('story_edit', story_id=story_id)
        except:
            messages.error(request, 'Could not update story')
    
    return render(request, 'author/story_edit.html', {'story': story})

def page_create(request, story_id):
    """Create a new page for a story"""
    if request.method == 'POST':
        data = {
            'text': request.POST.get('text'),
            'is_ending': request.POST.get('is_ending') == 'on',
            'ending_label': request.POST.get('ending_label', '')
        }
        try:
            response = requests.post(f"{FLASK_API}/stories/{story_id}/pages", json=data)
            if response.status_code == 201:
                messages.success(request, 'Page created!')
                return redirect('story_edit', story_id=story_id)
        except:
            messages.error(request, 'Could not create page')
    
    return render(request, 'author/page_form.html', {'story_id': story_id})

def choice_create(request, page_id):
    """Create a choice for a page"""
    if request.method == 'POST':
        data = {
            'text': request.POST.get('text'),
            'next_page_id': request.POST.get('next_page_id')
        }
        try:
            response = requests.post(f"{FLASK_API}/pages/{page_id}/choices", json=data)
            if response.status_code == 201:
                messages.success(request, 'Choice created!')
                # Redirect back to story edit
                # We need to track story_id somehow
        except:
            messages.error(request, 'Could not create choice')
    
    return render(request, 'author/choice_form.html', {'page_id': page_id})

def story_delete(request, story_id):
    """Delete a story"""
    if request.method == 'POST':
        try:
            response = requests.delete(f"{FLASK_API}/stories/{story_id}")
            if response.status_code == 204:
                messages.success(request, 'Story deleted!')
                return redirect('author_dashboard')
        except:
            messages.error(request, 'Could not delete story')
    
    return redirect('author_dashboard')

def story_list(request):
    """List all published stories with search"""
    search_query = request.GET.get('search', '')
    
    try:
        response = requests.get(f"{FLASK_API}/stories?status=published")
        stories = response.json() if response.status_code == 200 else []
        
        if search_query:
            stories = [s for s in stories if 
                      search_query.lower() in s['title'].lower() or 
                      search_query.lower() in s.get('description', '').lower()]
    except:
        stories = []
        messages.error(request, "Could not connect to story database")
    
    return render(request, 'stories/list.html', {
        'stories': stories,
        'search_query': search_query
    })

def play_story(request, story_id):
    """Start playing a story or resume"""
    # Check for existing session
    session_key = request.session.session_key or request.session.create()
    
    try:
        # Try to find existing session
        play_session = PlaySession.objects.get(
            session_key=session_key,
            story_id=story_id
        )
        # Resume from saved page
        return redirect('play_page', story_id=story_id, page_id=play_session.current_page_id)
    except PlaySession.DoesNotExist:
        # Start new game
        try:
            response = requests.get(f"{FLASK_API}/stories/{story_id}/start")
            if response.status_code == 200:
                page = response.json()
                
                # Create new session
                PlaySession.objects.create(
                    session_key=session_key,
                    story_id=story_id,
                    current_page_id=page['id']
                )
                
                return render(request, 'play/page.html', {
                    'story_id': story_id,
                    'page': page
                })
        except:
            messages.error(request, "Could not start story")
    
    return redirect('story_list')

def play_page(request, story_id, page_id):
    """Display a specific page during play"""
    session_key = request.session.session_key or request.session.create()
    
    try:
        response = requests.get(f"{FLASK_API}/pages/{page_id}")
        if response.status_code == 200:
            page = response.json()
            
            # Update session progress (if not ending)
            if not page.get('is_ending'):
                PlaySession.objects.update_or_create(
                    session_key=session_key,
                    story_id=story_id,
                    defaults={'current_page_id': page_id}
                )
            else:
                # Clear session on ending
                PlaySession.objects.filter(
                    session_key=session_key,
                    story_id=story_id
                ).delete()
                
                # Save play record
                Play.objects.create(
                    story_id=story_id,
                    ending_page_id=page_id
                )
            
            return render(request, 'play/page.html', {
                'story_id': story_id,
                'page': page
            })
    except:
        messages.error(request, "Could not load page")
    
    return redirect('story_list')

def story_detail(request, story_id):
    """View story details with enhanced statistics"""
    try:
        response = requests.get(f"{FLASK_API}/stories/{story_id}")
        story = response.json() if response.status_code == 200 else None
    except:
        story = None
        messages.error(request, "Could not load story")
    
    # Get enhanced statistics
    plays = Play.objects.filter(story_id=story_id)
    total_plays = plays.count()
    
    endings_stats = []
    if total_plays > 0:
        endings_data = plays.values('ending_page_id').annotate(count=Count('ending_page_id'))
        
        for ending in endings_data:
            # Get ending label from Flask
            try:
                page_response = requests.get(f"{FLASK_API}/pages/{ending['ending_page_id']}")
                if page_response.status_code == 200:
                    page_data = page_response.json()
                    percentage = (ending['count'] / total_plays) * 100
                    endings_stats.append({
                        'page_id': ending['ending_page_id'],
                        'label': page_data.get('ending_label', 'Unknown Ending'),
                        'count': ending['count'],
                        'percentage': round(percentage, 1)
                    })
            except:
                pass
    
    context = {
        'story': story,
        'total_plays': total_plays,
        'endings_stats': endings_stats
    }
    return render(request, 'stories/detail.html', context)

def story_create(request):
    """Create a new story"""
    if request.method == 'POST':
        data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description'),
            'status': request.POST.get('status', 'draft')  # Changed to draft
        }
        try:
            response = requests.post(f"{FLASK_API}/stories", json=data)
            if response.status_code == 201:
                story = response.json()
                messages.success(request, 'Story created as draft!')
                return redirect('story_edit', story_id=story['id'])
        except:
            messages.error(request, 'Could not create story')
    
    return render(request, 'author/story_form.html')

def story_publish(request, story_id):
    """Publish a draft story"""
    if request.method == 'POST':
        try:
            response = requests.put(
                f"{FLASK_API}/stories/{story_id}",
                json={'status': 'published'}
            )
            if response.status_code == 200:
                messages.success(request, 'Story published!')
        except:
            messages.error(request, 'Could not publish story')
    
    return redirect('story_edit', story_id=story_id)

def preview_story(request, story_id):
    """Preview a story without recording stats"""
    try:
        response = requests.get(f"{FLASK_API}/stories/{story_id}/start")
        if response.status_code == 200:
            page = response.json()
            return render(request, 'play/preview_page.html', {
                'story_id': story_id,
                'page': page,
                'preview_mode': True
            })
    except:
        messages.error(request, "Could not start preview")
    
    return redirect('author_dashboard')

def preview_page(request, story_id, page_id):
    """Preview a specific page"""
    try:
        response = requests.get(f"{FLASK_API}/pages/{page_id}")
        if response.status_code == 200:
            page = response.json()
            return render(request, 'play/preview_page.html', {
                'story_id': story_id,
                'page': page,
                'preview_mode': True
            })
    except:
        messages.error(request, "Could not load page")
    
    return redirect('author_dashboard')