from django.db import models
from django.contrib.auth.models import User

class Doctor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    lastMet = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
class MeetingHistory(models.Model):
    doctor = models.ForeignKey(Doctor, related_name="meetings", on_delete=models.CASCADE)
    meeting_date = models.DateField()
    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doctor.name} - {self.meeting_date}"