document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded event fired');
    const chatMessages = document.getElementById('chatMessages');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const fileInput = document.getElementById('fileInput');
    const resetButton = document.getElementById('resetButton');
    const typingIndicator = document.getElementById('typingIndicator');

    if (!chatMessages || !userInput || !sendButton || !fileInput || !resetButton || !typingIndicator) {
        console.log('One or more elements not found. User might not be logged in.');
        return;
    }

    function addMessage(content, isUser) {
        console.log(`Adding message: ${content}, isUser: ${isUser}`);
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'bot-message');
        messageDiv.textContent = content;
        chatMessages.appendChild(messageDiv);
        scrollToBottom();

        messageDiv.style.opacity = '0';
        messageDiv.style.transform = 'translateY(20px)';
        setTimeout(() => {
            messageDiv.style.opacity = '1';
            messageDiv.style.transform = 'translateY(0)';
        }, 50);
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

            console.log('Sending fetch request to /chat');
            fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            })
            .then(response => {
                console.log('Received response:', response);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Parsed response data:', data);
                hideTypingIndicator();
                addMessage(data.response, false);
            })
            .catch(error => {
                console.error('Error in fetch:', error);
                hideTypingIndicator();
                addMessage('An error occurred. Please try again.', false);
            });
        }
    }

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
        fetch('/reset_conversation', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                console.log('Reset conversation response:', data);
                chatMessages.innerHTML = '';
                addMessage("Conversation has been reset. How can I help you?", false);
            })
            .catch(error => {
                console.error('Error resetting conversation:', error);
                addMessage('An error occurred while resetting the conversation. Please try again.', false);
            });
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
            })
            .catch(error => {
                console.error('Error uploading file:', error);
                hideTypingIndicator();
                addMessage('An error occurred while uploading the file. Please try again.', false);
            });
        }
    });
});
