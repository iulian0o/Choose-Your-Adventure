from django.urls import path
from . import views

urlpatterns = [
    # Public browsing
    path('', views.story_list, name='story_list'),
    path('story/<int:story_id>/', views.story_detail, name='story_detail'),
    path('statistics/', views.statistics, name='statistics'),
    
    # Playing
    path('play/<int:story_id>/', views.play_story, name='play_story'),
    path('play/<int:story_id>/page/<int:page_id>/', views.play_page, name='play_page'),
    
    # Author tools
    path('author/', views.author_dashboard, name='author_dashboard'),
    path('author/story/create/', views.story_create, name='story_create'),
    path('author/story/<int:story_id>/edit/', views.story_edit, name='story_edit'),
    path('author/story/<int:story_id>/delete/', views.story_delete, name='story_delete'),
    path('author/story/<int:story_id>/page/create/', views.page_create, name='page_create'),
    path('author/page/<int:page_id>/choice/create/', views.choice_create, name='choice_create'),
]