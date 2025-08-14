from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sessions.backends.db import SessionStore
from django.utils.crypto import get_random_string
import json
import uuid
import traceback
import sys  
import os
import random
import string
import re
import requests
from django.http import HttpResponse
from django.http import JsonResponse
from groq import Groq
from llm_project_app.models import *
from datetime import datetime
from django.conf import settings

def all_entities_found(entity_list):
    return all(entity.get('entity_found', False) for entity in entity_list)
@csrf_exempt
def triage(request):
    chatbot_obj = json.loads(request.body.decode('utf-8'))
    print("Received chatbot_obj:", chatbot_obj)
    chat_input = chatbot_obj.get('chat_input', '').strip().lower()
    print("Chat input:", chat_input)
    first_question = chatbot_obj['first_question']
    Session = chatbot_obj['session']
    try: 
        patient_data_obj = chatbot_obj.get('patient_data_obj', {})
        print(patient_data_obj)
        question_answer_list = chatbot_obj.get('question_answer_list', [])
        if first_question:
            new_session_id =  get_random_string(32)
            chatbot_obj['Session'] = new_session_id
        if first_question:
            last_question = ''
            chatbot_obj['first_question'] = False
        else:
            if len(question_answer_list) >= 2:
                last_question = question_answer_list[-2].get('answer', '')
            else:
                last_question = ''
        groq_answer = generate_with_groq(
        chat_input,
        patient_data_obj,
        last_question
        )
        chatbot_obj['answer'] = groq_answer
        chatbot_obj['patient_data_obj'] = patient_data_obj
        print("Patient Data Object:", patient_data_obj)

        # Get the lists (default to empty list if not present)
        overview_list = patient_data_obj.get('overview_list', [])
        exam_labs_list = patient_data_obj.get('exam_labs_list', [])
        all_found = (
            all(entity.get('entity_found', False) for entity in overview_list)
            and 
             all(entity.get('entity_found', False) for entity in exam_labs_list)
            # all_entities_found(exam_labs_list)
        )
        # Age = chatbot_obj['patient_data_obj']['age'] 
        # Sex = chatbot_obj['patient_data_obj']['sex']
        if all_found:
            print("All entities found - running inference")
            chatbot_obj = process_inference(chatbot_obj)
            print("Run Inference output:", chatbot_obj)
            Sum  = summarize(question_answer_list)
            # title = f"{Age} {Sex} with {Sum}"
            title = f"{Sum}"
            print('title', title)
            chatbot_obj['title'] = title
        # else:

        chatbotObj = Chatbot.objects.filter(session=chatbot_obj['Session'], chat_user=chatbot_obj["user_id"]).first()
        if chatbotObj:
             chatbotObj.delete()

        if "recommendation" not in chatbot_obj:
            chatbot_obj["recommendation"] = ""

        chatbotObj = Chatbot(session=chatbot_obj['Session'], chat_user=chatbot_obj["user_id"], title=chatbot_obj["title"], answer=chatbot_obj["answer"], recommendation=chatbot_obj["recommendation"])
        # chatbotObj.first_question = chatbot_obj['first_question']
        chatbotObj.save()
        question_answer_list = chatbot_obj["question_answer_list"]
        for question_answer in question_answer_list:
            QuestionAnswer.objects.create(
                question=question_answer['question'],
                answer=question_answer['answer'],
                questionTimestamp = datetime.now(),
                answerTimestamp = datetime.now(),
                chatbot_obj=chatbotObj
            )
        patient_data, created = PatientData.objects.update_or_create(
            chatbot_obj=chatbotObj,
            defaults={
            'age': patient_data_obj.get('age'),
            'sex': patient_data_obj.get('sex')
            }
        )

        overview_list = patient_data_obj.get('overview_list', [])
        exam_labs_list = patient_data_obj.get('exam_labs_list', [])
        treatment_recommendations_list = patient_data_obj.get('treatment_recommendations_list', [])

        for entry in overview_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='overview',
                patient_data=patient_data
            )

        for entry in exam_labs_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='exam_lab',
                patient_data=patient_data
            )

        for entry in treatment_recommendations_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='treatment_recommendation',
                patient_data=patient_data
            )

    except Exception as e:
        traceback.print_exc()
    return HttpResponse(json.dumps(chatbot_obj), content_type='application/json')

@csrf_exempt
def triage_phone(request):
    chatbot_obj = json.loads(request.body.decode('utf-8'))
    print("Received chatbot_obj:", chatbot_obj)
    chat_input = chatbot_obj.get('chat_input', '').strip().lower()
    print("Chat input:", chat_input)
    first_question = chatbot_obj['first_question']
    Session = chatbot_obj['session']
    try: 
        patient_data_obj = chatbot_obj.get('patient_data_obj', {})
        print(patient_data_obj)
        question_answer_list = chatbot_obj.get('question_answer_list', [])
        if first_question:
            new_session_id =  get_random_string(32)
            chatbot_obj['Session'] = new_session_id
        if first_question:
            last_question = ''
            chatbot_obj['first_question'] = False
        else:
            if len(question_answer_list) >= 2:
                last_question = question_answer_list[-2].get('answer', '')
            else:
                last_question = ''

        print("Patient Data Object:", patient_data_obj)

        # Get the lists (default to empty list if not present)
        overview_list = patient_data_obj.get('overview_list', [])
        exam_labs_list = patient_data_obj.get('exam_labs_list', [])
        all_found = (
            all(entity.get('entity_found', False) for entity in overview_list)
            and 
             all(entity.get('entity_found', False) for entity in exam_labs_list)
            # all_entities_found(exam_labs_list)
        )
        # Age = chatbot_obj['patient_data_obj']['age'] 
        # Sex = chatbot_obj['patient_data_obj']['sex']
        if all_found:
            print("All entities found - running inference")
            # chatbot_obj = process_inference(chatbot_obj)
            print("Run Inference output:", chatbot_obj)
            Sum  = summarize(question_answer_list)
            # title = f"{Age} {Sex} with {Sum}"
            title = f"{Sum}"
            print('title', title)
            chatbot_obj['title'] = title
        # else:

        chatbotObj = Chatbot.objects.filter(session=chatbot_obj['Session'], chat_user=chatbot_obj["user_id"]).first()
        if chatbotObj:
             chatbotObj.delete()

        if "recommendation" not in chatbot_obj:
            chatbot_obj["recommendation"] = ""

        chatbotObj = Chatbot(session=chatbot_obj['Session'], chat_user=chatbot_obj["user_id"], title=chatbot_obj["title"], answer=chatbot_obj["answer"], recommendation=chatbot_obj["recommendation"])
        # chatbotObj.first_question = chatbot_obj['first_question']
        chatbotObj.save()
        question_answer_list = chatbot_obj["question_answer_list"]
        for question_answer in question_answer_list:
            QuestionAnswer.objects.create(
                question=question_answer['question'],
                answer=question_answer['answer'],
                questionTimestamp = datetime.now(),
                answerTimestamp = datetime.now(),
                chatbot_obj=chatbotObj
            )
        patient_data, created = PatientData.objects.update_or_create(
            chatbot_obj=chatbotObj,
            defaults={
            'age': patient_data_obj.get('age'),
            'sex': patient_data_obj.get('sex')
            }
        )

        overview_list = patient_data_obj.get('overview_list', [])
        exam_labs_list = patient_data_obj.get('exam_labs_list', [])
        treatment_recommendations_list = patient_data_obj.get('treatment_recommendations_list', [])

        for entry in overview_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='overview',
                patient_data=patient_data
            )

        for entry in exam_labs_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='exam_lab',
                patient_data=patient_data
            )

        for entry in treatment_recommendations_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='treatment_recommendation',
                patient_data=patient_data
            )

    except Exception as e:
        traceback.print_exc()
    return HttpResponse(json.dumps(chatbot_obj), content_type='application/json')
def summarize(history):
    try:
        # Create a string of Q&A
        qa_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in history])
        
        # Create the messages list PROPERLY
        messages = [
            {
                "role": "system", 
                "content": "Summarize this doctor-to-doctor conversation into one unique line with timestamp coming afterwards so that every conversation can be identified"
                # "if the recommendation is for ICU -  maybe mark it an emergency case (Emergency case of GI Bleed of Age Gender <date time>. Example:Emergency case of 68 yr old female with GI bleed with melena <date time>)  "
            },
            {
                "role": "user", 
                "content": f"Summarize the following conversation into a title of maximum 7 words, no extra words just title: {qa_text}"
            }
        ]

        client = Groq(api_key=settings.GROQ_API_KEY)
        summary_response = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages, 
            temperature=0,
        )
        
        
    except Exception as e:
        traceback.print_exc()
    return summary_response.choices[0].message.content
def all_entities_found(patient_data):
    overview_all_found = all(item['entity_found'] for item in patient_data['overview_list'])
    exam_labs_all_found = all(item['entity_found'] for item in patient_data['exam_labs_list'])
    return overview_all_found and exam_labs_all_found
    
def extract_and_update_entities(entities, patient_data):
    """
    Update patient_data_obj with extracted entities
    """
    entity_map = {}
    for item in entities:
        # Use the entity_found flag directly from NER response
        if 'name' in item and 'value' in item and 'entity_found' in item:
            entity_map[item['name']] = {
                'found': item['entity_found'],  
                'value': item['value']
            }
    if info := entity_map.get('Age'):
        if info['found']:
            patient_data['age'] = info['value']

    # Update sex if found
    if info := entity_map.get('Sex'):
        if info['found']:
            patient_data['sex'] = info['value']
    # Update overview_list (symptoms)
    for entry in patient_data.get('overview_list', []):
        if info := entity_map.get(entry['name']):
            entry['entity_found'] = info['found']
            entry['value'] = info['value']

    # Update exam_labs_list (lab values)
    for entry in patient_data.get('exam_labs_list', []):
        if info := entity_map.get(entry['name']):
            entry['entity_found'] = info['found']
            entry['value'] = info['value']
            
            # Handle numeric range checking
            if info['found'] and 'range' in entry:
                try:
                    # Convert to number if possible
                    num_val = float(info['value'])
                    lo, hi = map(float, entry['range'].split('-'))
                    entry['outside_range'] = not (lo <= num_val <= hi)
                except (ValueError, TypeError):
                    # Handle non-numeric values gracefully
                    entry['outside_range'] = False

def generate_with_groq(user_input, patient_data, latest_question):
    '''
    This function generates a response using the Groq API.
    Input: user_input, patient_data, latest_question
    Output: Groq API response
    '''
    response_format = {
        "type": "json_object",
        "schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {"type": "string"},
                            "entity_found": {"type": "boolean"}
                        },
                        "required": ["name", "value", "entity_found"]
                    }
                }
            },
            "required": ["entities"]
        }
    }
    
    # messages_for_NER = [
    #     {
    #         "role": "system",
    #         "content": "You are a medical assistant and you are talking with a doctor who is treating patient, Hence question should be 'has the patient' instead of 'do you have'"
    #         "Extract the terms only if they are mentioned in the user input. You are assigned to extract the medical terms and their values mentioned by the user. Return JSON matching the schema.For each entity, return an object with 'name', 'value' (boolean string), and 'entity_found' (boolean). "
    #     "Example: 'entities': [[{'name': 'Hematochezia', 'value': 'true', 'entity_found': true}, ...]"
    #     "Please ensure that you pass the enities in the standardized format. Example: International Normalized Ratio (INR) should be passed as INR, not International Normalized Ratio. "
    #     "Age, Sex, Hematochezia,Hematemesis,Melena,Duration,Syncope,Hx of GIB,Unstable CAD,COPD,CRF,Risk for stress ulcer,Cirrhosis,ASA/NSAID,PPI, SBP,DBP,HR,Orthostasis,NG lavage,Rectal,HCT,,HCT Drop,PLT,CR,BUN,INR"
    #     "Hematochezia and Hemetesis have three values - 'none','small','copious', Melena have three values - 'Brown', 'Dark', 'Pitch black'"
    #     "for other entities, if it is yes then it have to be present and if it is no, then absent"
    #     },
    #     {
    #         "role": "assistant",
    #         "content": latest_question
    #     },
    #     {"role": "user", "content": user_input}
    # ]

    messages_for_NER = [
        {
            "role": "system",
            "content": "You are a physician and you are talking with a doctor who is treating patient, Hence question should be 'has the patient' instead of 'do you have'. In the conversation, acknowledge when information is being provided to you, and if possible comment on the condition of the patient from the information you have received so far."
            "Extract the terms only if they are mentioned in the user input. You are assigned to extract the medical terms and their values mentioned by the user. Return JSON matching the schema.For each entity, return an object with 'name', 'value' (boolean string), and 'entity_found' (boolean). "
        "Example: 'entities': [[{'name': 'Hematochezia', 'value': 'true', 'entity_found': true}, ...]"
        "Please ensure that you pass the enities in the standardized format. Example: International Normalized Ratio (INR) should be passed as INR, not International Normalized Ratio. "
        "Age, Sex, Hematochezia,Hematemesis,Melena,Duration,Syncope,Hx of GIB,Unstable CAD,COPD,CRF,Risk for stress ulcer,Cirrhosis,ASA/NSAID,PPI, SBP,DBP,HR,Orthostasis,NG lavage,Rectal,HCT,,HCT Drop,PLT,CR,BUN,INR"
        "Hematochezia and Hemetesis have three values - 'none','small','copious', Melena have three values - 'Brown', 'Dark', 'Pitch black'"
        "for other entities, if it is yes then it have to be present and if it is no, then absent"
        },
        {
            "role": "assistant",
            "content": latest_question
        },
        {"role": "user", "content": user_input}
    ]
    
    print("Groq messages:", messages_for_NER)

    try:
        client = Groq(api_key=Groq_api_key)
        ner_response = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages_for_NER,
            temperature=0,
            response_format=response_format
        )
        
        content = ner_response.choices[0].message.content or "{}"
        result = json.loads(content)
        print("Content:", content)
        print("ner_response:", ner_response.choices[0].message)
        print("NER Result:", result)
        entities = result.get("entities", [])
        extract_and_update_entities(entities, patient_data)

        # Generate follow-up question
        missing = [
            item.get('name')
            for section in patient_data.values()
            if isinstance(section, list)
            for item in section
            if isinstance(item, dict) and not item.get('entity_found', False)
        ] + [
            key
            for key in ('age', 'sex')
            if not patient_data.get(key)
        ]

        follow_up_context = f" Missing data: {', '.join(missing)}. Ask one question about missing data. As this is late emergency night call, Be as natural as possible and direct questions and DO NOT ask about Source, Resuscitation, Emergent Endoscopy, ICU. Ask about multiple entities at once. example: what is his blood work"
        print("follow up", follow_up_context)
        messages_for_QG = [
            {"role": "system", "content": f"You are a medical assistant. {follow_up_context}"},
            {"role": "user", "content": user_input}
        ]
        
        qg_response = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages_for_QG,
            temperature=0.3,
            max_tokens=64
        )
        print("QG Response:", qg_response.choices[0].message.content)
        return qg_response.choices[0].message.content
        
    except Exception as e:
        traceback.print_exc()
        return "An error occurred while processing your request."
    
@csrf_exempt
def get_chat_history(request):
    
    chat_history_list = []

    try:

        data = json.loads(request.body.decode('utf-8'))
        user_id = data.get('user_id', None)
        chats = Chatbot.objects.all().order_by('-id')
        # chats = Chatbot.objects.filter(use).order_by('-id')
        

        for chat in chats:
            patient_data = PatientData.objects.filter(chatbot_obj=chat).first()
            print(chat.session)
            chat_history = {
                'id': chat.id,
                'title': chat.title,
                'age': patient_data.age if patient_data else None,
                'gender': patient_data.sex if patient_data else None,
                'condition': patient_data.overview if patient_data else None
            }
            question_answer_list = list(chat.question_answers.values('question', 'answer').order_by('id'))
            lastMessage = chat.answer if chat.answer is not None else "No message"
            timestamp = chat.question_answers.first().questionTimestamp if chat.question_answers.exists() else datetime.now()
            chat_history['lastMessage'] = lastMessage

            chat_history['timestamp'] = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            chat_history['messageCount'] = chat.question_answers.count()
            # chat_history['patientName'] = chat.chat_user
            # chat_history['title'] = chat.title if chat.title else "No Title"
            chat_history['session'] = chat.session
            # chat_history['chat_input'] = chat.chat_input if chat.chat_input else "No Input"
            # chat_history['answer'] = chat.answer if chat.answer else "No Answer"
            # chat_history['recommendation'] = chat.recommendation if chat.recommendation else "No Recommendation"
            # chat_history['chat_user'] = chat.chat_user
            if patient_data:
                chat_history['age'] = patient_data.age
                chat_history['gender'] = patient_data.sex
                # chat_history['condition'] = patient_data.overview_list[0].value if patient_data.overview_list else None

            # chat_history['session'] = chat.session
            # chat_history['title'] = getattr(chat, 'title', None)
            # chat_history['age'] = chat.patient_data_obj
            # chat_history['recommendation'] = getattr(chat, 'recommendation', None)
            chat_history['chatbot_id'] = chat.id  
            chat_history_list.append(chat_history)      
            # question_answers = chat.question_answers.all().values('question', 'answer')
            # chat_list.append({
            #     'id': chat.id,
            #     'session': chat.session,
            #     'title': getattr(chat, 'title', None),
            #     'recommendation': getattr(chat, 'recommendation', None),
            #     'question_answer_list': list(question_answers),
            #     'patient_data_obj': getattr(chat, 'patient_data_obj', {}),
            #     'final_recommendations_list': getattr(chat, 'final_recommendations_list', [])
            # })
        # return JsonResponse(chat_history_list, status=200)
        print(chat_history_list)
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
    return HttpResponse(json.dumps(chat_history_list), content_type='application/json')        

@csrf_exempt
def get_chat_details(request):
    try:
        chat_id = json.loads(request.body.decode('utf-8')).get('chat_id')
        # chat_id = json.loads(request.body.decode('utf-8'))

        chatbot_obj = Chatbot.objects.get(id=chat_id)
        question_answers = chatbot_obj.question_answers.all().order_by('id')
        qa_list = [
            {
                'question': qa.question,
                'answer': qa.answer,
                'question_timestamp': qa.questionTimestamp.isoformat() if qa.questionTimestamp else None,
                'answer_timestamp': qa.answerTimestamp.isoformat() if qa.answerTimestamp else None
            }
            for qa in question_answers
        ]
        patient_data = None
        try:
            patient_data_obj = PatientData.objects.get(chatbot_obj=chatbot_obj)
            patient_data = {
                'age': patient_data_obj.age,
                'sex': patient_data_obj.sex,
                # 'overview_list': patient_data_obj.overview_list,
                # 'exam_labs_list': patient_data_obj.exam_labs_list,
                # 'treatment_recommendations_list': patient_data_obj.treatment_recommendations_list
            }
            overview_list = patient_data_obj.entities.filter(named_entity_type='overview').values('name', 'value', 'entity_found', 'outside_range')
            exam_labs_list = patient_data_obj.entities.filter(named_entity_type='exam_lab').values('name', 'value', 'entity_found', 'outside_range')
            treatment_recommendations_list = patient_data_obj.entities.filter(named_entity_type='treatment_recommendation').values('name', 'value', 'entity_found', 'outside_range')
            patient_data['overview_list'] = list(overview_list)
            patient_data['exam_labs_list'] = list(exam_labs_list)
            patient_data['treatment_recommendations_list'] = list(treatment_recommendations_list)   
        except PatientData.DoesNotExist:
            pass
        response_data = {
            'id': chatbot_obj.id,
            'title': chatbot_obj.title,
            'session': chatbot_obj.session,
            'user_id': chatbot_obj.chat_user,
            'question_answer_list': qa_list,
            'patient_data_obj': patient_data,
            'answer': chatbot_obj.answer,
            'recommendation': chatbot_obj.recommendation,
            # 'created_at': chatbot_obj.created_at.isoformat() if chatbot_obj.created_at else None,
            # 'updated_at': chatbot_obj.updated_at.isoformat() if chatbot_obj.updated_at else None
        }
        print( " IIII ", response_data)
        return JsonResponse(response_data, status=200)
        
        
    except Exception as e:
        traceback.print_exc()
    return HttpResponse(json.dumps(chatbot_obj), content_type='application/json')  
def update_treatment_recommendations(treatment_list, chatbot_obj):
    """Update patient_data with extracted treatment recommendations"""
    # Create normalized mapping dictionary
    treatment_map = {}
    for item in treatment_list:
        # Normalize keys: lowercase and remove spaces
        normalized_name = item['name'].lower().replace(' ', '')
        treatment_map[normalized_name] = {
            'value': item['value'],
            'entity_found': item['entity_found'],
            'outside_range': item['outside_range']
        }

    # Access the nested treatment list
    patient_data = chatbot_obj.get('patient_data_obj', {})
    treatment_recs = patient_data.get('treatment_recommendations_list', [])
    
    for entry in treatment_recs:
        # Normalize entry name for matching
        entry_key = entry['name'].lower().replace(' ', '')
        
        if entry_key in treatment_map:
            info = treatment_map[entry_key]
            # Update the entry
            entry['value'] = info['value']
            entry['entity_found'] = info['entity_found']
            entry['outside_range'] = info['outside_range']
            print(f"Updated {entry['name']}: value={info['value']}, found={info['entity_found']}")
        else:
            print(f"No match for {entry['name']} (normalized: {entry_key})")


@csrf_exempt
def process_inference(input_chatbot_obj):
    '''Process inference for the chatbot object
    Input:
    input_chatbot_obj: dict - The chatbot object containing patient data and chat history
    Output:
    input_chatbot_obj: dict - The updated chatbot object with treatment recommendations and final answer
    This function extracts patient data, generates a summary, and runs inference to update treatment recommendations.
    It uses Groq for generating the summary and making predictions based on the patient's data.
    It also updates the chatbot object with the final recommendations and answer.
    It handles exceptions and prints the traceback for debugging.
    '''
    try:
        example_output = "54 year old Male presents with No hematochezia, copious blood clots hematemesis, reports melena, Patient reports symptoms for <1Day. Patient reports syncope, denies unstable CAD, denies COPD, denies CRF, denies risk for stress ulcer, denies cirrhosis, reports ASA/NSAID use, denies PPI use. Prior history of No GI bleed. BP is 100/60, HR 106 with orthistasis. NG lavage was coffee grounds, and rectal exam showed melanotic stool. Lab showed a hematocrit of 26, hematocrit drop from baseline of about 14, Platelets 266, Creatine 1.1 , BUN 38, INR 1.1"
        patient_data_obj = input_chatbot_obj.get('patient_data_obj', '')
        prompt = json.dumps(patient_data_obj)
        messages_for_summary = [
            {
                "role": "system",
                "content": "You are a medical assistant and you have given task to convert the JSON file into text. Only as example output no extra words"
                f"This is the example for expected output: {example_output}"},
            {"role": "user", "content": prompt}
        ]
        print("message summary:",messages_for_summary)
        client = Groq(api_key=Groq_api_key)
        response_for_summary = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages_for_summary,
            temperature=0,
        )
        summary = response_for_summary.choices[0].message.content or "{}"
              
        
        message_for_prediction = f" You have to triage the source, resuscitation, if urgent endoscopy required, if ICU is needed or Monitor or Regular room. you have to give the response in short form: Source:'',Resuscitation:'',Emergent Endoscopy:'',  if ICU is required:''. This is the information given by the patient: {summary}"
        print("prediction message:", message_for_prediction)
        payload = {
            "prompt": message_for_prediction,
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        print("Final message:",message_for_prediction)
        resp = requests.post("https://clinicianclone.com/infer_test/", json=payload, timeout=25)
        # resp = requests.post("http://198.145.127.41:8003/generate/", json=payload, timeout=25)

        
        resp.raise_for_status()
        agent_response = resp.text
        print("agent response",agent_response)
        messages_for_NER1 = [
        {
            "role": "system",
            "content": "You are a medical assistant. Extract ONLY the following treatment-related parameters EXPLICITLY MENTIONED in the clinical discussion: Source (Allowed values: 'Upper','Mid','Lower'), Resuscitation (Y/N), Emergent Endoscopy (Y/N), ICU (Y/N). Return JSON with 'treatment_recommendations_list' containing these 4 parameters in EXACT order. For each: 'name' , 'value' (extracted value (Should be exactly as Allowed Values) OR ''), 'entity_found' (true ONLY if explicitly mentioned), 'outside_range' (true ONLY if value invalid). if it is ICU then pass value as Y or for everything else it should be N"
        },
        {"role": "user", "content": agent_response}
       ]

        # Define the response format schema
        response_format1 = {
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    "treatment_recommendations_list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "entity_found": {"type": "boolean"},
                                "outside_range": {"type": "boolean"}
                            },
                            "required": ["name", "value", "entity_found", "outside_range"]
                        }
                    }
                },
                "required": ["treatment_recommendations_list"]
            }
        }

        client = Groq(api_key=Groq_api_key)
        ner_response1 = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages_for_NER1,
            temperature=0,
            response_format=response_format1  # Enforce schema
        )

        content1 = ner_response1.choices[0].message.content or "{}"
        result1 = json.loads(content1)
        def generate_recommendation_paragraph(data):
            source_val = None
            source_found = False
            resus_val = None
            endo_val = None
            icu_val = None

            for item in data['treatment_recommendations_list']:
                if item['name'] == 'Source':
                    source_val = item['value']
                    source_found = item['entity_found']
                elif item['name'] == 'Resuscitation':
                    resus_val = item['value']
                elif item['name'] == 'Emergent Endoscopy':
                    endo_val = item['value']
                elif item['name'] == 'ICU':
                    icu_val = item['value']

            sentences = []
            
            source_phrase = "a source of GI bleeding"
            if source_found and source_val:  # Only specify source if valid data exists
                source_phrase = f"a {source_val.lower()} source of GI bleeding"
            
            if resus_val == 'Y':
                source_phrase += " requiring resuscitation"
            elif resus_val == 'N':
                source_phrase += " not requiring resuscitation"
            
            sentences.append(f"This patient has {source_phrase}.")
            
            interventions = []
            
            if endo_val == 'Y':
                interventions.append("Urgent endoscopic intervention is indicated")
            elif endo_val == 'N':
                interventions.append("Urgent endoscopic intervention is not indicated")
                
            if icu_val == 'Y':
                interventions.append("ICU admission is indicated")
            elif icu_val == 'N':
                interventions.append("ICU admission is not indicated")
            
            if interventions:
                # Combine interventions with appropriate grammar
                if len(interventions) > 1:
                    interventions_str = ", ".join(interventions[:-1]) + " and " + interventions[-1]
                else:
                    interventions_str = interventions[0]
                sentences.append(interventions_str + ".")
            
            # Combine all sentences
            return " ".join(sentences)
        
        treatment_list = result1.get("treatment_recommendations_list", [])
        recommendation = generate_recommendation_paragraph(result1)
        print("recommendation", recommendation)
        update_treatment_recommendations(treatment_list, input_chatbot_obj)
        updated_treatment = input_chatbot_obj['patient_data_obj']['treatment_recommendations_list']
        print("Updated treatment_recommendations_list:", updated_treatment)
        def all_entities_found(entity_list):
            return all(entity.get('entity_found', False) for entity in entity_list)
        overview_list = patient_data_obj.get('overview_list', [])
        exam_labs_list = patient_data_obj.get('exam_labs_list', [])
        all_found = (
            all_entities_found(overview_list) and 
            all_entities_found(exam_labs_list)
        )
        if all_found:
            input_chatbot_obj['answer'] = "Thank you for the information, I have received all the information. You can check the side bar for final recommendations"
        input_chatbot_obj['recommendation'] = recommendation
    except Exception as e:
        traceback.print_exc()
    return input_chatbot_obj

@csrf_exempt
def run_inference(request):
    try:
        chatbot_obj = json.loads(request.body.decode('utf-8'))

        chatbot_obj['session'] = ''
        try: 
            patient_data_obj = chatbot_obj.get('patient_data_obj', {})
            question_answer_list = chatbot_obj.get('question_answer_list', [])
            # if first_question:
            new_session_id =  get_random_string(32)
            chatbot_obj['session'] = new_session_id
            last_question = ''
            chatbot_obj['first_question'] = False
            chat_input = chatbot_obj.get('chat_input', '')
            # else:
            #     if len(question_answer_list) >= 2:
            #         last_question = question_answer_list[-2].get('answer', '')
            #     else:
            #         last_question = ''
            groq_answer = generate_with_groq(
            chat_input,
            patient_data_obj,
            last_question
            )
            chatbot_obj['answer'] = groq_answer
            chatbot_obj['patient_data_obj'] = patient_data_obj
            print("Patient Data Object:", patient_data_obj)
            chatbot_obj['answer'] = ''
            chatbot_obj['patient_data_obj'] = patient_data_obj

            # Get the lists (default to empty list if not present)
            overview_list = patient_data_obj.get('overview_list', [])
            exam_labs_list = patient_data_obj.get('exam_labs_list', [])
            all_found = (
                all(entity.get('entity_found', False) for entity in overview_list)
                and 
                all(entity.get('entity_found', False) for entity in exam_labs_list)
                # all_entities_found(exam_labs_list)
            )

            updated_chatbot_obj = process_inference(chatbot_obj)
            
            print("Run Inference output:", chatbot_obj)
            Sum  = summarize(question_answer_list)
            title = f"{Sum}"
            print('title', title)
            chatbot_obj['title'] = title
        except Exception as e:
            traceback.print_exc()       
        chatbotObj = Chatbot.objects.filter(session=chatbot_obj['session'], chat_user=chatbot_obj["user_id"]).first()
        if chatbotObj:
             chatbotObj.delete()

        if "recommendation" not in chatbot_obj:
            chatbot_obj["recommendation"] = ""

        chatbotObj = Chatbot(session=chatbot_obj['session'], chat_user=chatbot_obj["user_id"], title=chatbot_obj["title"], answer=chatbot_obj["answer"], recommendation=chatbot_obj["recommendation"])
        # chatbotObj.first_question = chatbot_obj['first_question']
        chatbotObj.save()
        question_answer_list = chatbot_obj["question_answer_list"]
        for question_answer in question_answer_list:
            QuestionAnswer.objects.create(
                question=question_answer['question'],
                answer=question_answer['answer'],
                questionTimestamp = datetime.now(),
                answerTimestamp = datetime.now(),
                chatbot_obj=chatbotObj
            )
        patient_data, created = PatientData.objects.update_or_create(
            chatbot_obj=chatbotObj,
            defaults={
            'age': patient_data_obj.get('age'),
            'sex': patient_data_obj.get('sex')
            }
        )

        overview_list = patient_data_obj.get('overview_list', [])
        exam_labs_list = patient_data_obj.get('exam_labs_list', [])
        treatment_recommendations_list = patient_data_obj.get('treatment_recommendations_list', [])

        for entry in overview_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='overview',
                patient_data=patient_data
            )

        for entry in exam_labs_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='exam_lab',
                patient_data=patient_data
            )

        for entry in treatment_recommendations_list:
            NamedEntity.objects.create(
                name=entry.get('name'),
                value=entry.get('value'),
                entity_found=entry.get('entity_found', False),
                outside_range=entry.get('outside_range', False),
                named_entity_type='treatment_recommendation',
                patient_data=patient_data
            )


    except Exception as e:
        traceback.print_exc()
    
    return HttpResponse(
            json.dumps(updated_chatbot_obj), 
            content_type='application/json'
        )



