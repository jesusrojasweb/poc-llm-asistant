// static/js/main.js

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded event fired');
    const socket = io();
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const fileInput = document.getElementById('fileInput');
    const resetButton = document.getElementById('resetButton');
    const typingIndicator = document.getElementById('typingIndicator');
    const converter = new showdown.Converter();
    let messageCounter = 0;
    const chatList = document.getElementById('chatList');
    const createChatButton = document.getElementById('createChatButton');

    if (!chatMessages || !userInput || !sendButton || !fileInput || !resetButton || !typingIndicator || !chatList || !createChatButton) {
        console.log('One or more elements not found. User might not be logged in.');
        return;
    }

    // Función para cargar la lista de chats
    function loadChats() {
        fetch('/chats')
            .then(response => response.json())
            .then(chats => {
                chatList.innerHTML = '';
                chats.forEach(chat => {
                    const li = document.createElement('li');
                    li.textContent = chat.title;
                    li.dataset.chatId = chat.id;
                    li.addEventListener('click', () => selectChat(chat.id));
                    chatList.appendChild(li);
                });

                // Si hay un chat activo en la sesión, seleccionarlo
                const activeChatId = sessionStorage.getItem('activeChatId');
                if (activeChatId) {
                    const activeChatElement = chatList.querySelector(`li[data-chat-id="${activeChatId}"]`);
                    if (activeChatElement) {
                        activeChatElement.classList.add('active-chat');
                        selectChat(activeChatId);
                    }
                } else if (chats.length > 0) {
                    // Seleccionar el primer chat por defecto
                    selectChat(chats[0].id);
                }
            })
            .catch(error => console.error('Error cargando chats:', error));
    }

    // Función para seleccionar un chat
    function selectChat(chatId) {
        // Resaltar el chat seleccionado
        Array.from(chatList.children).forEach(li => {
            li.classList.toggle('active-chat', li.dataset.chatId === String(chatId));
        });

        // Actualizar el chat activo en la sesión del navegador
        sessionStorage.setItem('activeChatId', chatId);

        // Enviar una solicitud al servidor para seleccionar el chat
        fetch('/chats/select', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ chat_id: chatId }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Emitir un evento de Socket.IO para actualizar la sesión en el servidor
                socket.emit('join_chat', { chat_id: chatId });

                // Cargar los mensajes del chat seleccionado
                fetch(`/chats/${chatId}/messages`)
                    .then(response => response.json())
                    .then(history => {
                        chatMessages.innerHTML = '';
                        history.forEach(msg => addMessage(msg.content, msg.is_user, msg.message_id, msg.feedback, msg.thereIsFeedback));
                        hideTypingIndicator();
                    })
                    .catch(error => console.error('Error seleccionando chat:', error));
            }
        })
        .catch(error => console.error('Error seleccionando chat:', error));
    }

    // Función para crear un nuevo chat
    function createNewChat() {
        const title = prompt('Ingrese el título del nuevo chat:', 'Nuevo Chat');
        if (title !== null && title.trim() !== '') {
            fetch('/chats/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ title: title.trim() }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    loadChats();
                    selectChat(data.chat_id);
                }
            })
            .catch(error => console.error('Error creando nuevo chat:', error));
        }
    }

    // Event listener para el botón de crear chat
    createChatButton.addEventListener('click', createNewChat);

    // Cargar chats al inicio
    loadChats();

    function addMessage(content, isUser, messageId = null, feedback = null, thereIsFeedback) {
        console.log(`Adding message: ${content}, isUser: ${isUser}, messageId: ${messageId}, feedback: ${feedback}, thereIsFeedback: ${thereIsFeedback}`);
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        const html = converter.makeHtml(content);
        messageDiv.innerHTML = html;

        if (!messageId) {
            messageId = `temp-${messageCounter++}`;
        }
        messageDiv.setAttribute('id', `msg-${messageId}`);

        if (!isUser) {
            const feedbackDiv = document.createElement('div');
            feedbackDiv.classList.add('message-feedback');
            feedbackDiv.innerHTML = `
                <button class="feedback-btn like${(feedback === true && thereIsFeedback) ? ' active' : ''}" data-message-id="${messageId}">
                    <i data-feather="thumbs-up"></i>
                </button>
                <button class="feedback-btn dislike${(feedback === false && thereIsFeedback) ? ' active' : ''}" data-message-id="${messageId}">
                    <i data-feather="thumbs-down"></i>
                </button>
            `;
            messageDiv.appendChild(feedbackDiv);
        }

        chatMessages.appendChild(messageDiv);
        scrollToBottom();

        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        setTimeout(() => {
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 50);

        feather.replace();
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function showTypingIndicator() {
        console.log('Showing typing indicator');
        typingIndicator.style.display = 'flex';
        scrollToBottom();
    }

    function hideTypingIndicator() {
        console.log('Hiding typing indicator');
        typingIndicator.style.display = 'none';
    }

    function sendMessage() {
        const message = userInput.value.trim();
        if (message) {
            console.log('Sending message:', message);
            addMessage(message, true);
            userInput.value = '';
            showTypingIndicator();

            socket.emit('send_message', { message: message });
        }
    }

    socket.on('receive_message', (data) => {
        console.log('Received message:', data);
        hideTypingIndicator();
        addMessage(data.message, data.is_user, data.message_id);
    });

    socket.on('conversation_reset', () => {
        console.log('Conversation reset');
        chatMessages.innerHTML = '';
        addMessage("¡Hola! Soy tu compañero de estudios para los cursos de Mazda en Lapzo. Estoy aquí para ayudarte a resolver cualquier duda sobre el contenido de los cursos de manera rápida y clara. Si alguna pregunta es muy compleja, la escalaré a un instructor o administrador. ¡Comencemos!", false);
    });

    socket.on('joined_chat', (data) => {
        console.log(`Joined chat with ID: ${data.chat_id}`);
    });

    socket.on('error', (data) => {
        console.error(`Error: ${data.message}`);
    });

    console.log('Attaching event listeners');
    sendButton.addEventListener('click', (e) => {
        e.preventDefault();
        console.log('Send button clicked');
        sendButton.classList.add('shake');
        setTimeout(() => {
            sendButton.classList.remove('shake');
        }, 500);
        sendMessage();
    });

    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            console.log('Enter key pressed');
            sendMessage();
        }
    });

    resetButton.addEventListener('click', () => {
        console.log('Reset button clicked');
        resetButton.classList.add('shake');
        setTimeout(() => {
            resetButton.classList.remove('shake');
        }, 500);
        socket.emit('reset_conversation');
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            console.log('File selected:', file.name);
            const formData = new FormData();
            formData.append('file', file);
            showTypingIndicator();
            fetch('/upload', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                console.log('File upload response:', data);
                hideTypingIndicator();
                addMessage(`File uploaded: ${data.file_url}`, true);
                if (file.name.toLowerCase().endsWith('.pdf')) {
                    addMessage("PDF uploaded successfully. You can now ask questions about its content.", false);
                }
            })
            .catch(error => {
                console.error('Error uploading file:', error);
                hideTypingIndicator();
                addMessage('An error occurred while uploading the file. Please try again.', false);
            });
        }
    });

    document.addEventListener('click', function(e) {
        if (e.target.closest('.feedback-btn')) {
            const button = e.target.closest('.feedback-btn');
            const messageId = button.getAttribute('data-message-id');
            const isLike = button.classList.contains('like');

            // Remove active class from both buttons
            button.parentNode.querySelectorAll('.feedback-btn').forEach(btn => btn.classList.remove('active'));

            // Add active class to clicked button
            button.classList.add('active');

            fetch('/feedback', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message_id: messageId,
                    is_like: isLike
                }),
            })
            .then(response => response.json())
            .then(data => {
                console.log('Feedback sent successfully:', data);
            })
            .catch((error) => {
                console.error('Error sending feedback:', error);
            });
        }
    });
});
