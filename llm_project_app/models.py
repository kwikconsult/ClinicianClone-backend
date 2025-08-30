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
    chain_of_thought = models.TextField(blank=True, null=True)
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
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    title = models.CharField(max_length=512, blank=True, null=True)
    chat_input = models.TextField(blank=True, null=True)
    chain_of_thought = models.TextField(blank=True, null=True)
    answer = models.TextField(blank=True, null=True)
    recommendation = models.TextField(blank=True, null=True)
    def __unicode__(self):
        return self.session

class ChatbotSettings(models.Model):
    
    ner_model_name = models.CharField(max_length=255,blank=True, null=True)
    ner_model_context = models.TextField(blank=True, null=True)
    ner_model_temperature = models.FloatField(blank=True, null=True)
    ner_model_max_tokens = models.IntegerField(blank=True, null=True)
    ner_model_top_p = models.IntegerField(blank=True, null=True)
    ner_model_json_response = models.BooleanField(blank=True, null=True)
    ner_model_response_format = models.TextField(blank=True, null=True)

    follow_up_model_name = models.CharField(max_length=255, blank=True, null=True)
    follow_up_model_context = models.CharField(max_length=255, blank=True, null=True)
    follow_up_model_temperature = models.FloatField(blank=True, null=True)
    follow_up_model_max_tokens = models.IntegerField(blank=True, null=True)
    follow_up_model_top_p = models.IntegerField(blank=True, null=True)
    follow_up_model_json_response = models.BooleanField(blank=True, null=True)
    follow_up_model_response_format = models.TextField(blank=True, null=True)
    
    summarise_model_name = models.CharField(max_length=255,blank=True, null=True)
    summarise_model_system_context = models.TextField(blank=True, null=True)
    summarise_model_user_context = models.TextField(blank=True, null=True)
    summarise_model_temperature = models.FloatField(blank=True, null=True)
    summarise_model_max_tokens = models.IntegerField(blank=True, null=True)
    summarise_model_top_p = models.IntegerField(blank=True, null=True)
    summarise_model_json_response = models.BooleanField(blank=True, null=True)
    summarise_model_response_format = models.TextField(blank=True, null=True)
    
    prediction_model_name = models.CharField(max_length=255,blank=True, null=True)
    prediction_model_context = models.CharField(max_length=255, blank=True, null=True)
    prediction_model_temperature = models.FloatField(blank=True, null=True)
    prediction_model_max_tokens = models.IntegerField(blank=True, null=True)
    prediction_model_top_p = models.FloatField(blank=True, null=True)
    prediction_model_json_response = models.BooleanField(blank=True, null=True)
    prediction_model_response_format = models.TextField(blank=True, null=True)

    treatment_recommendation_model_name = models.CharField(max_length=255, blank=True, null=True)
    treatment_recommendation_model_context = models.TextField(blank=True, null=True)
    treatment_recommendation_model_temperature = models.FloatField(blank=True, null=True)
    treatment_max_tokens = models.IntegerField(blank=True, null=True)
    treatment_model_top_p = models.FloatField(blank=True, null=True)
    treatment_recommendation_model_json_response = models.BooleanField(blank=True, null=True)
    treatment_recommendation_model_response_format = models.TextField(blank=True, null=True)
    
    def __unicode__(self):
        return self.session