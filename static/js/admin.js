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
                updateCharts(data.chart_data);
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
                displayChatStats(data.stats);
            });
    }

    function displayChatHistory(history) {
        chatHistory.innerHTML = '';
        history.forEach(message => {
            const div = document.createElement('div');
            div.classList.add('message', message.is_user ? 'user-message' : 'bot-message');
            div.innerHTML = `
                <p>${message.content}</p>
                <small>${new Date(message.timestamp).toLocaleString()}</small>
                <span class="feedback">${getFeedbackIcon(message.feedback)}</span>
            `;
            chatHistory.appendChild(div);
        });
        smoothScrollToBottom(chatHistory);
    }

    function getFeedbackIcon(feedback) {
        if (feedback === true) return '👍';
        if (feedback === false) return '👎';
        return '';
    }

    function displayChatStats(stats) {
        const statsDiv = document.createElement('div');
        statsDiv.classList.add('chat-stats');
        statsDiv.innerHTML = `
            <p>Total Messages: ${stats.total_messages}</p>
            <p>Likes: ${stats.likes_count}</p>
            <p>Dislikes: ${stats.dislikes_count}</p>
        `;
        chatHistory.prepend(statsDiv);
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

    function updateCharts(chartData) {
        updateUserActivityChart(chartData.user_activity);
        updateMessageDistributionChart(chartData.message_distribution);
    }

    function updateUserActivityChart(data) {
        const ctx = document.getElementById('userActivityChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'User Activity',
                    data: data.values,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    function updateMessageDistributionChart(data) {
        const ctx = document.getElementById('messageDistributionChart').getContext('2d');
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['User Messages', 'Bot Messages', 'Likes', 'Dislikes'],
                datasets: [{
                    data: [data.user_messages, data.bot_messages, data.likes, data.dislikes],
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(255, 206, 86, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true
            }
        });
    }

    userSearch.addEventListener('input', () => {
        currentPage = 1;
        fetchUsers(currentPage, userSearch.value);
    });

    fetchUsers();
});
