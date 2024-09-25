import os
from openai import OpenAI
from typing import List, Dict, Any, Optional
from openai.types.beta import Assistant

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

assistant: Optional[Assistant] = None
thread = None

def initialize_assistant():
    global assistant
    
    # Create a new assistant
    assistant = client.beta.assistants.create(
        name="PDF Assistant",
        instructions="You are a helpful assistant that can answer questions based on uploaded PDF documents.",
        model="gpt-4-1106-preview",
        tools=[{"type": "retrieval"}]
    )
    
    # Upload the initial PDF file
    pdf_path = "pdf-test.pdf"
    if os.path.exists(pdf_path):
        file = client.files.create(
            file=open(pdf_path, "rb"),
            purpose='assistants'
        )
        
        # Update the assistant to use the new file
        if assistant:
            assistant = client.beta.assistants.update(
                assistant_id=assistant.id,
                file_ids=[file.id]
            )
        print(f"Uploaded {pdf_path} to the assistant.")
    else:
        print(f"Error: {pdf_path} not found.")

def initialize_conversation(initial_history: Optional[List[Dict[str, str]]] = None):
    global thread
    thread = client.beta.threads.create()
    if initial_history:
        for message in initial_history:
            role = message['role']
            if role not in ['user', 'assistant']:
                role = 'user'  # Default to 'user' if an invalid role is provided
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role=role,
                content=message['content']
            )

def get_chatbot_response(user_message: str) -> str:
    global thread, assistant
    
    if thread is None:
        thread = client.beta.threads.create()
    
    if assistant is None:
        initialize_assistant()
    
    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )
    
    if assistant:
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )
        
        while run.status != "completed":
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        if messages.data and messages.data[0].content:
            content = messages.data[0].content[0]
            if hasattr(content, 'text'):
                return content.text.value
    return "No response from the assistant."

def reset_conversation():
    global thread
    thread = None
    initialize_conversation()

def upload_pdf(file_path: str) -> bool:
    try:
        file = client.files.create(
            file=open(file_path, "rb"),
            purpose='assistants'
        )
        
        # Update the assistant to use the new file
        global assistant
        if assistant:
            assistant = client.beta.assistants.update(
                assistant_id=assistant.id,
                file_ids=[file.id]
            )
        print(f"File uploaded successfully: {file.id}")
        return True
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return False

# Initialize the assistant when the module is imported
initialize_assistant()
