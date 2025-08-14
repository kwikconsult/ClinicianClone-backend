# test_views2.py
import os
import django
import json
import time

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "llm_project_app.settings")
django.setup()

# Import models
from django.test import RequestFactory
from llm_project_app.models import Chatbot, PatientData, NamedEntity, QuestionAnswer

# Import your view AFTER setup
from llm_project_app.views import triage

# test create chatbot
def test_create_chatbot():
    # Create unique session ID
    session_id = f"test_session_{int(time.time())}"
    
    chatbot_obj = Chatbot(
        session=session_id,
        chat_input="xyz",
        answer="999",
        first_question=False,
        treatment_recommendations=["medicines"],
    )
    chatbot_obj.save()
    qa1 = QuestionAnswer(
        question="What is the patient's age?",
        answer="45",
        chatbot_obj=chatbot_obj
    )
    qa1.save()

    qa2 = QuestionAnswer(
        question="What is the patient's gender?",
        answer="male",
        chatbot_obj=chatbot_obj
    )
    qa2.save()
    
    chatbot_obj.question_answers.add(qa1, qa2)
    chatbot_obj.save()
    
    return chatbot_obj

# test save
# test get chathistory
def test_triage_endpoint():
    # Create test data
    test_data = {
        "session": f"triage_test_{int(time.time())}",
        "chat_input": "64 year old female with melena",
        "first_question": True
    }
    
    # Create a mock request with JSON data
    factory = RequestFactory()
    request = factory.post('/triage', 
                          data=json.dumps(test_data),
                          content_type='application/json')

    # Call the view function
    response = triage(request)

    # Print results
    print("Status Code:", response.status_code)
    print("Response Content:", response.content.decode())
    
    return response

if __name__ == "__main__":
    # Run the tests
    print("Testing chatbot creation...")
    chatbot = test_create_chatbot()
    print(f"Created chatbot with session: {chatbot.session}")
    
    print("\nTesting triage endpoint...")
    response = test_triage_endpoint()