from django.db import models
from django.contrib.auth.models import User

class NamedEntity(models.Model):
    name = models.CharField(max_length=255,blank = True, null=True)
    value = models.CharField(max_length=255,blank = True, null=True)
    entity_found = models.BooleanField(default=False)
    outside_range = models.BooleanField(default=False)
    named_entity_type = models.CharField(max_length=255, blank=True, null=True)
    patient_data = models.ForeignKey('PatientData', on_delete=models.CASCADE, related_name='entities', blank=True, null=True)
    def __unicode__(self):
        return self.name

class QuestionAnswer(models.Model):
    question = models.TextField()
    answer = models.TextField(blank = True, null=True)
    questionTimestamp = models.DateTimeField(auto_now_add=True)
    answerTimestamp = models.DateTimeField(auto_now=True)
    chatbot_obj = models.ForeignKey('Chatbot', on_delete=models.CASCADE, related_name='question_answers', blank=True, null=True)
    def __unicode__(self):
        return self.question

class PatientData(models.Model):
    age = models.CharField(max_length=3, blank=True, null=True)
    sex = models.CharField(max_length=10, blank=True, null=True)
    overview = models.TextField(blank=True, null=True)
    exam_labs = models.TextField(blank=True, null=True)
    treatment_recommendations = models.TextField(blank=True, null=True)
    chatbot_obj = models.ForeignKey('Chatbot', on_delete=models.CASCADE)
    def __unicode__(self):
        return self.question

class ChatUser(models.Model):
    name = models.CharField(max_length=256, blank=True, null=True)
    email = models.EmailField(max_length=256, blank=True, null=True)
    def __unicode__(self):
        return self.name  

class Chatbot(models.Model):
    first_question = models.BooleanField(default=True)
    session = models.CharField(max_length=255, unique=True)
    # chat_user = models.ForeignKey('ChatUser', on_delete=models.CASCADE)
    chat_user = models.TextField(max_length=256, blank=True, null=True)

    title = models.CharField(max_length=512, blank=True, null=True)
    chat_input = models.TextField(blank=True, null=True)
    answer = models.TextField(blank=True, null=True)
    recommendation = models.TextField(blank=True, null=True)
    def __unicode__(self):
        return self.session
