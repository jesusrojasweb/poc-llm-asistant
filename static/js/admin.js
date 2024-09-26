document.addEventListener('DOMContentLoaded', () => {
    const userList = document.getElementById('user-list');
    const userSearch = document.getElementById('user-search');
    const userPagination = document.getElementById('user-pagination');
    const chatHistory = document.getElementById('chat-history');
    const totalUsers = document.getElementById('total-users');
    const totalMessages = document.getElementById('total-messages');
    const avgMessagesPerUser = document.getElementById('avg-messages-per-user');

    let currentPage = 1;
    const usersPerPage = 10;

    function fetchUsers(page = 1, search = '') {
        fetch(`/admin/users?page=${page}&search=${search}`)
            .then(response => response.json())
            .then(data => {
                displayUsers(data.users);
                updatePagination(data.total_pages, page);
                updateStatistics(data.statistics);
            });
    }

    function displayUsers(users) {
        userList.innerHTML = '';
        users.forEach(user => {
            const li = document.createElement('li');
            li.textContent = user.username;
            li.onclick = () => fetchUserChatHistory(user.id);
            userList.appendChild(li);
        });
    }

    function updatePagination(totalPages, currentPage) {
        userPagination.innerHTML = '';
        for (let i = 1; i <= totalPages; i++) {
            const button = document.createElement('button');
            button.textContent = i;
            button.onclick = () => fetchUsers(i, userSearch.value);
            if (i === currentPage) {
                button.disabled = true;
            }
            userPagination.appendChild(button);
        }
    }

    function updateStatistics(stats) {
        totalUsers.textContent = stats.total_users;
        totalMessages.textContent = stats.total_messages;
        avgMessagesPerUser.textContent = stats.avg_messages_per_user.toFixed(2);
    }

    function fetchUserChatHistory(userId) {
        showLoadingIndicator();
        fetch(`/admin/user_chat_history/${userId}`)
            .then(response => response.json())
            .then(data => {
                hideLoadingIndicator();
                displayChatHistory(data.chat_history);
            });
    }

    function displayChatHistory(history) {
        chatHistory.innerHTML = '';
        history.forEach(message => {
            const div = document.createElement('div');
            div.classList.add('message', message.is_user ? 'user-message' : 'bot-message');
            div.textContent = message.content;
            chatHistory.appendChild(div);
        });
        smoothScrollToBottom(chatHistory);
    }

    function showLoadingIndicator() {
        const loadingIndicator = document.createElement('div');
        loadingIndicator.id = 'loading-indicator';
        loadingIndicator.textContent = 'Loading...';
        chatHistory.innerHTML = '';
        chatHistory.appendChild(loadingIndicator);
    }

    function hideLoadingIndicator() {
        const loadingIndicator = document.getElementById('loading-indicator');
        if (loadingIndicator) {
            loadingIndicator.remove();
        }
    }

    function smoothScrollToBottom(element) {
        element.scrollTo({
            top: element.scrollHeight,
            behavior: 'smooth'
        });
    }

    userSearch.addEventListener('input', () => {
        currentPage = 1;
        fetchUsers(currentPage, userSearch.value);
    });

    fetchUsers();
});
