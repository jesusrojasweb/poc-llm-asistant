import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

assistant = None
thread = None
vector_store = None

def initialize_assistant():
    global assistant, vector_store
    
    # Create a new assistant
    assistant = client.beta.assistants.create(
        name="PDF Assistant",
        instructions="You are a helpful assistant that can answer questions based on uploaded PDF documents.",
        model="gpt-4o",
        tools=[{"type": "file_search"}]
    )

    # Crear un vector store para almacenar los archivos PDF
    vector_store = client.beta.vector_stores.create(name="PDF Knowledge Base")

    # Ruta de los archivos PDF a cargar
    pdf_paths = ["pdf-test.pdf", "pdf-test-1.pdf", "pdf-test-2.pdf"]

    # Preparar los archivos para subirlos al vector store
    file_streams = []
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            file_streams.append(open(pdf_path, "rb"))
        else:
            print(f"Error: {pdf_path} no encontrado.")
            
    if file_streams:
        # Subir los archivos y esperar a que se procesen
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=file_streams
        )
        print("Archivos subidos al vector store.")

        # Actualizar el asistente para usar el nuevo vector store
        assistant = client.beta.assistants.update(
            assistant_id=assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
        )
        print(f"Asistente actualizado con vector store ID {vector_store.id}")
    else:
        print("No hay archivos para subir.")
    
    
def initialize_conversation(initial_history=None):
    global thread
    thread = client.beta.threads.create()
    if initial_history:
        for message in initial_history:
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role=message['role'],
                content=message['content']
            )

def get_chatbot_response(user_message: str) -> str:
    global thread

    if thread is None:
        thread = client.beta.threads.create()

    # Añadir el mensaje del usuario al hilo
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message
    )

    # Crear una ejecución (run) del asistente
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    # Esperar a que la ejecución se complete
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    # Obtener la respuesta del asistente
    messages = client.beta.threads.messages.list(thread_id=thread.id)

    # Filtrar los mensajes para obtener los del asistente
    assistant_messages = [msg for msg in messages.data if msg.role == 'assistant']

    # Ordenar los mensajes por tiempo de creación
    assistant_messages.sort(key=lambda x: x.created_at)

    if assistant_messages:
        last_assistant_message = assistant_messages[-1]  # Último mensaje del asistente
        return last_assistant_message.content[0].text.value
    else:
        return "No se encontró respuesta del asistente."

def reset_conversation():
    global thread
    thread = None
    initialize_conversation()

# Añade esta función para obtener el vector_store_id
def get_vector_store_id():
    global vector_store
    return vector_store.id

def upload_pdf(file_url, vector_store_id):
    try:
        file_streams = []
        pdf_path = f"static{file_url}"
        print(pdf_path)
        if os.path.exists(pdf_path):
            file_streams.append(open(pdf_path, "rb"))
        else:
            print(f"Error: {file_url} no encontrado.")

        if file_streams:
            # Subir el archivo al vector store y esperar a que se procese
            file = client.beta.vector_stores.files.create_and_poll(
                vector_store_id=vector_store_id,
                files=file_streams
            )
            print(f"Archivo subido exitosamente al vector store: {file.id}")
        return True
    except Exception as e:
        print(f"Error al subir el archivo: {str(e)}")
        return False

# Initialize the assistant when the module is imported
initialize_assistant()
