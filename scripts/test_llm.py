'''
A script that tests out calls to grow (17B llama model) for Comprehensive list of NER 
1. Named Entity Recognition 
2. Response (use information provided and if needed NER) 
3. Summary of the case so far (summary of question) 
4. Treatment recommendations 
5. Save output at each stage to a file
6. Add execution time at each stage
7. Test with different testcases and parameter values
8. Chain of thought - at each stage
9. Possible recommendations at each stage
10. chromadb
11. FAISS
12. Medgamma
'''

import traceback
import os
import argparse
import json
import sys
import django
import time
import requests
from groq import Groq
from datetime import datetime

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "llm_project_app.settings")
django.setup()

from django.conf import settings

# If django import fails
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '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')

# user_params = [Age, Sex, Hematochezia,Hematemesis,Melena,Duration,Syncope,Hx of GIB,Unstable CAD,COPD,CRF,Risk for stress ulcer]

# str_params = (", ").join(user_params)

from llm_project_app.models import PatientData, Chatbot
from llm_project_app.views import extract_and_update_entities, update_treatment_recommendations

# Test inputs
TEST_INPUTS1 = [
    {"user": "I've got an 80-year-old male here, Mr. Peterson. He's been having melena for about two days, and his wife says he had a syncopal episode at home this morning. He's been on a high dose of ASA for some unstable CAD, and he also takes a PPI, but he's not very compliant"},
    {"user": "He was pretty hypotensive when he came in. His SBP was 85, DBP 50, and HR 125. We've got two large-bore IVs in and he's responding to fluids. His most recent vitals are 105/65, HR 105, but he's orthostatic"},
    {"user": "The lavage was clear, but the rectal exam was guaiac positive with melenic stool, so the bleed is definitely there, just not active enough to be showing up in the stomach"},
    {"user": "His initial Hct was 28, but it's dropped to 22 since we started resuscitation. Plt is 140, Cr is 1.8, and BUN is 45. His INR is also high at 1.9"},
    {"user": "He does present with copious blood stool, also hematemesis and has a history of GI Bleed"},
    {"user": "He does present with CRF, COPD, cirrhosis and there is risk for stress ulcer"}
]

# TEST_INPUTS2 = [
#     {"user": "I've got an 80-year-old male here, Mr. Peterson. He's been having melena for about two days, and his wife says he had a syncopal episode at home this morning. He's been on a high dose of ASA for some unstable CAD, and he also takes a PPI, but he's not very compliant"},
#     {"user": "He was pretty hypotensive when he came in. His SBP was 85, DBP 50, and HR 125. We've got two large-bore IVs in and he's responding to fluids. His most recent vitals are 105/65, HR 105, but he's orthostatic"},
#     {"user": "The lavage was clear, but the rectal exam was guaiac positive with melenic stool, so the bleed is definitely there, just not active enough to be showing up in the stomach"},
#     {"user": "His initial Hct was 28, but it's dropped to 22 since we started resuscitation. Plt is 140, Cr is 1.8, and BUN is 45. His INR is also high at 1.9"},
#     {"user": "He does present with copious blood stool, also hematemesis and has a history of GI Bleed"},
#     {"user": "He does present with CRF, COPD, cirrhosis and there is risk for stress ulcer"}
# ]

SETTINGS_OBJ = {

    "ner_model_name":"meta-llama/llama-4-maverick-17b-128e-instruct",
    "ner_model_context":"You are discussing a patient with a physician in a natural conversational style. Summarize the data when asked."
        "Extract medical terms and corresponding values mentioned by the user. Return JSON matching the schema. For each entity, return an object with 'name', 'value' (boolean string), and 'entity_found' (boolean)."
        "Example: 'entities': [[{'name': 'Hematochezia', 'value': 'true', 'entity_found': true}, ...]"
        "Extract the entities only mentioned in the user input. If an entity is not mentioned, don't include it in the response."
        "Give the response if it is yes then it have to be Yes and if it is no, then No."
        "Pass the entities as a standardized format. Example: International Normalized Ratio (INR) should be passed as INR, not International Normalized Ratio."
        "Age, Sex, Hematochezia,Hematemesis,Melena,Duration,Syncope,Hx of GIB,Unstable CAD,COPD,CRF,Risk for stress ulcer, Cirrhosis,ASA/NSAID,PPI, SBP,DBP,HR,Orthostasis,NG lavage,Rectal,HCT,HCT Drop,PLT,CR,BUN,INR"
        "Hematochezia and Hemetesis have three values - 'none','small','copious', Melena have three values - 'Brown', 'Dark', 'Pitch black'"
        "for other entities, if it is yes then it have to be Yes and if it is no, then No. ",
    "ner_model_temperature":0,

    "follow_up_model_name":"meta-llama/llama-4-maverick-17b-128e-instruct",
    "follow_up_model_context":"Collect data about variables: Missing Data. Keep questions short and terse, Be as natural as possible and direct questions and DO NOT ask about Source, Resuscitation, Emergent Endoscopy or ICU. Combine multiple missing entities into one question. Example: 'What is their blood work?",
    "follow_up_model_temperature":0.3,
    "follow_up_model_max_tokens":64,
    
    "summarise_model_name":"meta-llama/llama-4-maverick-17b-128e-instruct",
    "summarise_model_system_context":"You are a medical assistant and you have given task to convert the JSON file into text. Only as example output no extra words",
    "summarise_model_user_context":"",
    "summarise_model_temperature":0,

    "prediction_model_name":"meta-llama/llama-4-maverick-17b-128e-instruct",
    "prediction_model_context":"You have to triage the source, resuscitation, if urgent endoscopy required, if ICU is needed or Monitor or Regular room. you have to give the response in short form: Source:'',Resuscitation:'',Emergent Endoscopy:'',  if ICU is required:''. Also provide the chain_of_thought behind why do you think the bleeding is from particular sourse, why do you think emergent endoscopy is required/not required, why do you think reusitation is required/not required, why do you think ICU admission is required/not_required. under 'chain_of_thought'. This is the information given by the patient:",
    "prediction_model_max_tokens":1024,
    "prediction_model_temperature":0.7,
    "prediction_model_top_p": 0.9,

    "treatment_recommendation_model_name":"meta-llama/llama-4-maverick-17b-128e-instruct",
    "treatment_recommendation_model_context":"You are a medical assistant. Extract ONLY the following treatment-related parameters EXPLICITLY MENTIONED in the clinical discussion: Source (Allowed values: 'Upper','Mid','Lower'), Resuscitation (Y/N), Emergent Endoscopy (Y/N), ICU (Y/N). Return JSON with 'treatment_recommendations_list' containing these 4 parameters in EXACT order. also for the 'chain_of_thought' return the string of explanation given by the LLM, direct Chain of thought on getting those results, don't repeat the terms. For each: 'name' , 'value' (extracted value (Should be exactly as Allowed Values) OR ''), 'entity_found' (true ONLY if explicitly mentioned), 'outside_range' (true ONLY if value invalid). if it is ICU then pass value as Y or for everything else it should be N. Explain your reasoning process in detail and return the thought process in the JSON as 'chain_of_thought'.",
    "treatment_recommendation_model_temperature":0,
    "treatment_recommendation_model_response_format":{
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
                    },
                    "chain_of_thought": {
                        "type": "string"
                    }
                },
                "required" : ["treatment_recommendations_list", "chain_of_thought"]
            }
        }
}

# To save into an output file
class TestLogger:
    def __init__(self):
        self.results = {
            "test_timestamp": datetime.now().isoformat(),
            "settings": SETTINGS_OBJ,
            "conversation_flow": [],
            "execution_times": {}
        }
        self.timers = {}

    def start_timer(self, name):
        self.timers[name] = time.time()

    def stop_timer(self, name):
        if name in self.timers:
            elapsed_time = time.time() - self.timers[name]
            self.results["execution_times"][name] = f"{elapsed_time:.3f} seconds"
            return elapsed_time
        return 0

    def log_interaction(self, stage, user_input, assistant_response, parameters= None):
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "user_input": user_input,
            "assistant_response": assistant_response,
            "parameters": parameters or {}
        }
        self.results["conversation_flow"].append(interaction)
    
    def log_final_result(self, summary, treatment, chain_of_thought):
        self.results["final_results"] = {
            "summary": summary,
            "treatment_recommendation": treatment,
            "chain_of_thought": chain_of_thought,
            "timestamp": datetime.now().isoformat()
        }

    def save(self, filename=None):
        if not filename:
            filename = f"run_grok_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"Results saved to {filename}")
        return filename

def generate_with_groq(user_input, patient_data, latest_question, settings_obj, logger):
    logger.start_timer("ner_followup")
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

    messages_for_NER = [
        {
            "role": "system",
            "content": settings_obj["ner_model_context"]
        },
        {
            "role": "assistant",
            "content": latest_question
        },
        {"role": "user", "content": user_input}
    ]

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        ner_response = client.chat.completions.create(
            model=settings_obj["ner_model_name"],
            messages=messages_for_NER,
            temperature=settings_obj["ner_model_temperature"],
            response_format=response_format
        )

        content = ner_response.choices[0].message.content or "{}"
        result = json.loads(content)
        entities = result.get("entities", [])
        
        extract_and_update_entities(entities, patient_data)

        # Check for missing entities
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

        follow_up_context = f"Missing data: {', '.join(missing)}. " + settings_obj["follow_up_model_context"]
        
        messages_for_QG = [
            {"role": "system", "content": f"You are a medical assistant. {follow_up_context}"},
            {"role": "user", "content": user_input}
        ]
        
        qg_response = client.chat.completions.create(
            model=settings_obj["follow_up_model_name"],
            messages=messages_for_QG,
            temperature=settings_obj["follow_up_model_temperature"],
            max_tokens=settings_obj["follow_up_model_max_tokens"]
        )

        follow_up_question = qg_response.choices[0].message.content
        
        # Log this interaction
        logger.log_interaction(
            "ner_followup",
            user_input,
            follow_up_question,
            {
                "ner_model": settings_obj["ner_model_name"],
                "ner_temperature": settings_obj["ner_model_temperature"],
                "follow_up_model": settings_obj["follow_up_model_name"],
                "follow_up_temperature": settings_obj["follow_up_model_temperature"],
                "follow_up_max_tokens": settings_obj["follow_up_model_max_tokens"],
                "missing_entities": missing
            }
        )
        elapsed_time = logger.stop_timer("ner_followup")
        return follow_up_question
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        logger.log_interaction("error", user_input, error_msg, patient_data.copy())
        return error_msg

def process_inference(chatbot_obj, settings_obj, logger):
    try:
        logger.start_timer("summary_generation")
        patient_data_obj = chatbot_obj.get('patient_data_obj', '')
        
        # Convert patient data to text summary
        messages_for_summary = [
            {
                "role": "system",
                "content": settings_obj["summarise_model_system_context"]
            },
            {"role": "user", "content": json.dumps(patient_data_obj)}
        ]

        client = Groq(api_key=settings.GROQ_API_KEY)
        response_for_summary = client.chat.completions.create(
            model=settings_obj["summarise_model_name"],
            messages=messages_for_summary,
            temperature=settings_obj["summarise_model_temperature"]
        )

        summary = response_for_summary.choices[0].message.content or "{}"
        elapsed_time_summary = logger.stop_timer("summary_generation")
        # Log summary generation
        logger.log_interaction(
            "summary",
            "Generate summary from patient data",
            summary,
            {
                "model": settings_obj["summarise_model_name"],
                "temperature": settings_obj["summarise_model_temperature"],
                "executed_time":f"{elapsed_time_summary:.3f} seconds"
            }
        )

        logger.start_timer("prediction_generation")
        message_for_prediction = settings_obj["prediction_model_context"] + summary
        payload = {
            "prompt": message_for_prediction,
            "max_tokens": settings_obj["prediction_model_max_tokens"] ,
            "temperature": settings_obj["prediction_model_temperature"] ,
            "top_p": settings_obj["prediction_model_top_p"] ,
        }

        resp = requests.post("https://clinicianclone.com/infer_test/", json=payload, timeout=25)
        resp.raise_for_status()
        agent_response = resp.text
        elapsed_time_prediction = logger.stop_timer("prediction_generation")
        print("agent response",agent_response)

        # Log API response
        logger.log_interaction(
            "inference_api",
            "External API call",
            agent_response,
            {
                "api_endpoint": "https://clinicianclone.com/infer_test/",
                "max_tokens": settings_obj["prediction_model_max_tokens"],
                "temperature": settings_obj["prediction_model_temperature"],
                "top_p": settings_obj["prediction_model_top_p"],
                "executed_time":f"{elapsed_time_prediction:.3f} seconds"
            }
        )

        logger.start_timer("treatment_extraction")
        messages_for_treatment = [
        {
            "role": "system",
            "content": settings_obj["treatment_recommendation_model_context"]
        },
        {"role": "user", "content": agent_response}
       ]

        client = Groq(api_key=settings.GROQ_API_KEY)

        treatment_response = client.chat.completions.create(
            model=settings_obj['treatment_recommendation_model_name'],
            messages=messages_for_treatment,
            temperature=settings_obj['treatment_recommendation_model_temperature'],
            response_format=settings_obj['treatment_recommendation_model_response_format']
        )

        treatment_json = treatment_response.choices[0].message.content or "{}"
        treatment_data = json.loads(treatment_json)
        print("Treatment Response:", treatment_data)
        elapsed_time_treatment = logger.stop_timer("treatment_extraction")

        # Log treatment extraction
        logger.log_interaction(
            "treatment_extraction",
            "Extract treatment from API response",
            json.dumps(treatment_data, indent=2),
            {
                "model": settings_obj["treatment_recommendation_model_name"],
                "temperature": settings_obj["treatment_recommendation_model_temperature"],
                "executed_time": f"{elapsed_time_treatment:.3f} seconds"
            }
        )

        logger.start_timer("recommendation_generation")
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
            if source_found and source_val:
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

        treatment_list = treatment_data.get("treatment_recommendations_list", [])
        chain_of_thought = treatment_data.get("chain_of_thought", "")

        recommendation = generate_recommendation_paragraph(treatment_data)

        overview_list = patient_data_obj.get('overview_list', [])
        exam_labs_list = patient_data_obj.get('exam_labs_list', [])
        all_found = (
            all(entity.get('entity_found', False) for entity in overview_list)
            and
            all(entity.get('entity_found', False) for entity in exam_labs_list)
        )
        if all_found:
            chatbot_obj['answer'] = "Thank you for the information, I have received all the information. You can check the side bar for final recommendations"
        elapsed_time_recommendation = logger.stop_timer("recommendation_generation")
        chatbot_obj['recommendation'] = recommendation
        chatbot_obj['chain_of_thought'] = chain_of_thought
        
    except Exception as e:
        traceback.print_exc()
    return chatbot_obj

def main():
    print("Testing...")
    
    logger = TestLogger()
    logger.start_timer("total_execution")

    # Initialize chatbot object
    chatbot_obj = {
        'first_question': True,
        'session': 'test_session_123',
        'user_id': 'test_user',
        'title': 'Test Conversation',
        'answer': '',
        'recommendation': '',
        'chain_of_thought': '',
        'patient_data_obj': {
            'age': None,
            'sex': None,
            'overview_list': [
                {'name': 'Hematochezia', 'value': None, 'entity_found': False},
                {'name': 'Hematemesis', 'value': None, 'entity_found': False},
                {'name': 'Melena', 'value': None, 'entity_found': False},
                {'name': 'Duration', 'value': None, 'entity_found': False},
                {'name': 'Syncope', 'value': None, 'entity_found': False},
                {'name': 'Hx of GIB', 'value': None, 'entity_found': False},
                {'name': 'Unstable CAD', 'value': None, 'entity_found': False},
                {'name': 'COPD', 'value': None, 'entity_found': False},
                {'name': 'CRF', 'value': None, 'entity_found': False},
                {'name': 'Risk for stress ulcer', 'value': None, 'entity_found': False},
                {'name': 'Cirrhosis', 'value': None, 'entity_found': False},
                {'name': 'ASA/NSAID', 'value': None, 'entity_found': False},
                {'name': 'PPI', 'value': None, 'entity_found': False}
            ],
            'exam_labs_list': [
                {'name': 'SBP', 'value': None, 'entity_found': False, 'range': '90-140'},
                {'name': 'DBP', 'value': None, 'entity_found': False, 'range': '60-90'},
                {'name': 'HR', 'value': None, 'entity_found': False, 'range': '60-100'},
                {'name': 'Orthostasis', 'value': None, 'entity_found': False},
                {'name': 'NG lavage', 'value': None, 'entity_found': False},
                {'name': 'Rectal', 'value': None, 'entity_found': False},
                {'name': 'HCT', 'value': None, 'entity_found': False, 'range': '36-48'},
                {'name': 'HCT Drop', 'value': None, 'entity_found': False},
                {'name': 'PLT', 'value': None, 'entity_found': False, 'range': '150-450'},
                {'name': 'CR', 'value': None, 'entity_found': False, 'range': '0.6-1.2'},
                {'name': 'BUN', 'value': None, 'entity_found': False, 'range': '7-20'},
                {'name': 'INR', 'value': None, 'entity_found': False, 'range': '0.8-1.2'}
            ]
        },
        'question_answer_list': []
    }
    
    latest_question = "Please describe the patient's symptoms and medical history."
    
    # Simulate the conversation flow
    for i, conversation_turn in enumerate(TEST_INPUTS):
        user_input = conversation_turn['user']
        print(f"\n User Input {i+1}: {user_input}")
        
        # Process through NER & Follow-up
        groq_answer = generate_with_groq(
            user_input,
            chatbot_obj['patient_data_obj'],
            latest_question,
            SETTINGS_OBJ,
            logger
        )
        
        # Update conversation state
        chatbot_obj['answer'] = groq_answer
        chatbot_obj['question_answer_list'].append({
            'question': latest_question,
            'answer': user_input
        })
        
        latest_question = groq_answer
        print(f" Assistant: {groq_answer}")
    
    # Check if all entities are found
    overview_list = chatbot_obj['patient_data_obj'].get('overview_list', [])
    exam_labs_list = chatbot_obj['patient_data_obj'].get('exam_labs_list', [])
    
    all_found = (
        all(entity.get('entity_found', False) for entity in overview_list) and
        all(entity.get('entity_found', False) for entity in exam_labs_list)
    )

    if all_found:
        print("\n All entities collected! Running inference...")
        chatbot_obj = process_inference(chatbot_obj, SETTINGS_OBJ, logger)
        print(f"Final Recommendation: ", chatbot_obj['recommendation'])

    total_time = logger.stop_timer("total_execution")

    # Save complete results
    output_file = logger.save()
    print(f"\n Complete test results saved to: {output_file}")

if __name__ == "__main__":
    main()