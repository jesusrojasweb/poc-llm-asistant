import os
from openai import OpenAI
from openai.types.beta import Assistant
from openai.types.beta.thread import Thread
from openai.types.beta.threads.thread_message import ThreadMessage

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

assistant: Assistant = None
thread: Thread = None

def initialize_assistant():
    global assistant
    assistant = client.beta.assistants.create(
        name="PDF Assistant",
        instructions="You are a helpful assistant that can answer questions based on uploaded PDF documents.",
        model="gpt-4-1106-preview"
    )

def create_thread():
    global thread
    thread = client.beta.threads.create()

def get_chatbot_response(user_message: str) -> str:
    global thread
    if thread is None:
        create_thread()

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    return messages.data[0].content[0].text.value

def reset_conversation():
    global thread
    thread = None
    create_thread()

def upload_pdf(file_path: str):
    file = client.files.create(
        file=open(file_path, "rb"),
        purpose="assistants"
    )
    client.beta.assistants.files.create(assistant_id=assistant.id, file_id=file.id)

# Initialize the assistant when the module is imported
initialize_assistant()
