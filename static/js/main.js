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

    if (!chatMessages || !userInput || !sendButton || !fileInput || !resetButton || !typingIndicator) {
        console.log('One or more elements not found. User might not be logged in.');
        return;
    }

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
        typingIndicator.style.display = 'block';
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

    fetch('/history')
        .then(response => response.json())
        .then(history => {
            history.forEach(msg => addMessage(msg.content, msg.is_user, msg.message_id, msg.feedback, msg.thereIsFeedback));
        })
        .catch(error => {
            console.error('Error loading chat history:', error);
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