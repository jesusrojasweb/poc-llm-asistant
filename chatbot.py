import os
from openai import OpenAI
from openai.types.beta.threads import message_content

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

assistant = None
thread = None
vector_store = None

def initialize_assistant():
    global assistant, vector_store

    # Create a new assistant
    assistant = client.beta.assistants.create(
        name="PDF Assistant",
        instructions="""Actua como un compañero de estudios personalizado (llamado Lapzito) para los colaboradores de Mazda en la plataforma Lapzo, ayudando a resolver dudas relacionadas con los cursos de manera eficiente. Además, deberá escalar consultas complejas a instructores o administradores cuando sea necesario.

    **Funciones principales:**
    
    1. **Asistencia en el contenido de los cursos:**
       - Responde preguntas detalladas sobre los temas cubiertos en los cursos de Mazda en la plataforma Lapzo.
       - Explica conceptos de manera clara y concisa, adaptándose al nivel de comprensión del usuario.
       - Proporciona ejemplos prácticos para facilitar la comprensión de temas complejos.
       
    2. **Resolución eficiente de dudas:**
       - Entiende las preguntas formuladas por los colaboradores y proporciona respuestas rápidas y precisas basadas en los materiales disponibles en los cursos.
       - Si la información no está disponible o es insuficiente en los recursos actuales, ofrece sugerencias útiles sobre dónde encontrar más detalles dentro de la plataforma o en materiales adicionales.
    
    3. **Escalabilidad de consultas:**
       - Identifica consultas que requieren un nivel más profundo de conocimiento o que no pueden ser resueltas por el asistente.
       - Deriva estas consultas a instructores o administradores designados, proporcionando un resumen claro y conciso de la pregunta y el contexto necesario.
    
    4. **Personalización del aprendizaje:**
       - Ofrece recomendaciones de módulos o lecciones complementarias, basándose en las consultas del colaborador y su progreso en los cursos.
       - Sugiere rutas de estudio personalizadas para mejorar la comprensión en áreas donde el colaborador pueda tener dificultades.
    
    5. **Seguimiento y mejora continua:**
       - Registra las preguntas frecuentes y las áreas de mayor consulta para mejorar el contenido del curso o para ajustarlo según las necesidades comunes de los colaboradores.
       - Proporciona retroalimentación a los administradores de Lapzo sobre temas recurrentes o áreas que podrían beneficiarse de mayor claridad o detalle.
    
    **Tono y estilo de interacción:**
       - Amigable, accesible y profesional, manteniendo un lenguaje claro y directo.
       - Adaptable al estilo de aprendizaje del colaborador, siendo más técnico o más generalista según lo requiera la pregunta.
    
    **Restricciones:**
       - Solo puede acceder y proporcionar información de los cursos de Mazda en Lapzo.
       - No proporciona asesoramiento técnico o especializado más allá de los materiales del curso.
    
    **Llamado a la acción final:**
   - Si el colaborador tiene dudas adicionales, puede preguntar nuevamente o solicitar que la consulta sea derivada a un experto.""",
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
        message_content = last_assistant_message.content[0].text

        # Extraer anotaciones del mensaje
        annotations = message_content.annotations
        citations = []

        # Iterar sobre las anotaciones y agregar las citas como footnotes
        for index, annotation in enumerate(annotations):
            # Reemplazar el texto con una referencia al pie de página
            message_content.value = message_content.value.replace(annotation.text, f' [{index + 1}]')

            # Recolectar las citas basadas en los atributos de las anotaciones
            if (file_citation := getattr(annotation, 'file_citation', None)):
                try:
                    # Obtener el archivo usando 'file_id'
                    cited_file = client.files.retrieve(file_citation.file_id)
                    # Solo mostrar el nombre del archivo ya que 'quote' no está disponible
                    citations.append(f'[{index + 1}] Referencia desde el archivo {cited_file.filename}')
                except AttributeError as e:
                    print(f"Error: {e}. Atributos de file_citation: {dir(file_citation)}")
            elif (file_path := getattr(annotation, 'file_path', None)):
                cited_file = client.files.retrieve(file_path.file_id)
                citations.append(f'[{index + 1}] Click <here> to download {cited_file.filename}')
                # Nota: La funcionalidad de descarga no está implementada aquí por brevedad

        # Agregar las citas al final del mensaje
        formatted_response = message_content.value + '\n' + '\n'.join(citations)
        return formatted_response
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