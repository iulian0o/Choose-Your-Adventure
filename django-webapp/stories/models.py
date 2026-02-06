from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Play(models.Model):
    # Trqck completed story plqythroughts
    story_id = models.IntegerField()
    ending_page_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Play #{self.id} - Story {self.story_id} - Ending {self.ending_page_id}"


class PlaySession(models.Model):
    # Track in-progress gameplay sessions
    session_key = models.CharField(max_length=100, unique=True)
    story_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    path_history = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Session {self.session_key} - Story {self.story_id}"


class Rating(models.Model):
    # Story ratings
    story_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('story_id', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - Story {self.story_id} - {self.score}★"


class Raport(models.Model):
    # Story reports for moderation 
    REASON_CHOICES = [
        ('inappropriate', 'Inappropriate Content'),
        ('spam', 'Spam'),
        ('offensive', 'Offensive Language'),
        ('broken', 'Broken/Unplayable'),
        ('other', 'Other'),
    ]
    
    story_id = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_reports')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report #{self.id} - Story {self.story_id} - {self.reason}"
