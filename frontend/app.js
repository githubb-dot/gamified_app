// Main application JavaScript for Alone, I Level Up app

const { createApp, ref, reactive, onMounted, computed, watch } = Vue;

const app = createApp({
    setup() {
        // Authentication state
        const isAuthenticated = ref(false);
        const authScreen = ref('login');
        const user = ref({});
        
        // Form data
        const loginForm = reactive({
            username: '',
            password: ''
        });
        
        const registerForm = reactive({
            username: '',
            email: '',
            password: '',
            improvement_goals: ['']
        });
        
        // App data
        const dashboard = reactive({
            title: 'Alone, I Level Up',
            stats: {
                strength: 0,
                intelligence: 0,
                discipline: 0,
                focus: 0,
                communication: 0,
                adaptability: 0
            },
            daily_quests: [],
            optional_quests: [],
            level: {
                level: 1,
                total_xp: 0,
                available_points: 0,
                next_level_xp: 1000,
                progress_percent: 0
            },
            notifications: []
        });
        
        const goals = ref([]);
        
        const newGoal = reactive({
            description: '',
            category: ''
        });
        
        // Level up animation
        const showLevelUpAnimation = ref(false);
        const levelUpDetails = reactive({
            newLevel: 1,
            pointsGained: 0
        });
        
        // Notifications system
        const notifications = ref([]);
        let notificationId = 0;
        
        const addNotification = (title, message, type = 'info') => {
            const id = notificationId++;
            notifications.value.push({ id, title, message, type });
            
            // Auto-remove after 5 seconds
            setTimeout(() => {
                removeNotification(id);
            }, 5000);
        };
        
        const removeNotification = (id) => {
            const index = notifications.value.findIndex(n => n.id === id);
            if (index !== -1) {
                notifications.value.splice(index, 1);
            }
        };
        
        // Registration helpers
        const addImprovementGoal = () => {
            registerForm.improvement_goals.push('');
        };
        
        const removeImprovementGoal = (index) => {
            registerForm.improvement_goals.splice(index, 1);
            // Ensure at least one goal field is always present
            if (registerForm.improvement_goals.length === 0) {
                registerForm.improvement_goals.push('');
            }
        };
        
        // Authentication methods
        const login = async () => {
            try {
                const response = await axios.post('/api/login', loginForm);
                user.value = response.data.user;
                isAuthenticated.value = true;
                
                // Load dashboard data
                await loadDashboard();
                await loadGoals();
                
                addNotification('Welcome back!', `You are now logged in as ${user.value.username}`, 'success');
            } catch (error) {
                console.error('Login error:', error);
                addNotification('Login Failed', error.response?.data?.error || 'Invalid username or password', 'error');
            }
        };
        
        const register = async () => {
            try {
                // Filter out empty improvement goals
                const filteredGoals = registerForm.improvement_goals.filter(goal => goal.trim() !== '');
                
                if (filteredGoals.length === 0) {
                    addNotification('Registration Error', 'Please add at least one improvement goal', 'error');
                    return;
                }
                
                const registrationData = {
                    username: registerForm.username,
                    email: registerForm.email,
                    password: registerForm.password,
                    improvement_goals: filteredGoals
                };
                
                const response = await axios.post('/api/register', registrationData);
                user.value = response.data.user;
                isAuthenticated.value = true;
                
                // Load dashboard data
                await loadDashboard();
                await loadGoals();
                
                addNotification('Registration Successful', 'Your account has been created with your improvement goals!', 'success');
            } catch (error) {
                console.error('Registration error:', error);
                addNotification('Registration Failed', error.response?.data?.error || 'Could not create account', 'error');
            }
        };
        
        const logout = async () => {
            try {
                await axios.post('/api/logout');
                isAuthenticated.value = false;
                user.value = {};
                authScreen.value = 'login';
                
                addNotification('Logged Out', 'You have been logged out successfully', 'info');
            } catch (error) {
                console.error('Logout error:', error);
            }
        };
        
        // Dashboard methods
        const loadDashboard = async () => {
            try {
                const response = await axios.get('/api/dashboard');
                dashboard.title = response.data.title;
                dashboard.stats = response.data.stats;
                dashboard.daily_quests = response.data.daily_quests || [];
                dashboard.optional_quests = response.data.optional_quests || [];
                dashboard.level = response.data.level;
                
                // Process notifications
                if (response.data.notifications && response.data.notifications.length > 0) {
                    response.data.notifications.forEach(notification => {
                        addNotification(notification.title, notification.message, notification.type);
                    });
                    
                    // Mark notifications as read
                    const notificationIds = response.data.notifications.map(n => n.id);
                    if (notificationIds.length > 0) {
                        await axios.post('/api/notifications/mark-read', { notification_ids: notificationIds });
                    }
                }
            } catch (error) {
                console.error('Dashboard loading error:', error);
                addNotification('Error', 'Failed to load dashboard data', 'error');
            }
        };
        
        // Goals methods
        const loadGoals = async () => {
            try {
                const response = await axios.get('/api/goals');
                goals.value = response.data.goals;
            } catch (error) {
                console.error('Goals loading error:', error);
                addNotification('Error', 'Failed to load goals', 'error');
            }
        };
        
        const createGoal = async () => {
            if (!newGoal.description) {
                addNotification('Error', 'Goal description is required', 'error');
                return;
            }
            
            try {
                const response = await axios.post('/api/goals', {
                    description: newGoal.description,
                    category: newGoal.category
                });
                
                // Add new goal to list
                goals.value.push(response.data.goal);
                
                // Clear form
                newGoal.description = '';
                newGoal.category = '';
                
                // Refresh dashboard to get any new quests
                await loadDashboard();
                
                addNotification('Goal Created', 'Your new improvement goal has been added!', 'success');
            } catch (error) {
                console.error('Goal creation error:', error);
                addNotification('Error', 'Failed to create goal', 'error');
            }
        };
        
        const deleteGoal = async (goalId) => {
            try {
                await axios.delete(`/api/goals/${goalId}`);
                
                // Remove goal from list
                const index = goals.value.findIndex(g => g.id === goalId);
                if (index !== -1) {
                    goals.value.splice(index, 1);
                }
                
                addNotification('Goal Deleted', 'Your goal has been removed', 'info');
            } catch (error) {
                console.error('Goal deletion error:', error);
                addNotification('Error', 'Failed to delete goal', 'error');
            }
        };
        
        // Quest methods
        const completeQuest = async (questId) => {
            try {
                const response = await axios.post(`/api/quests/${questId}/complete`);
                
                // Update dashboard
                await loadDashboard();
                
                // Check if user leveled up
                if (response.data.level_up) {
                    // Show level up animation
                    levelUpDetails.newLevel = response.data.new_level;
                    levelUpDetails.pointsGained = response.data.points_gained;
                    showLevelUpAnimation.value = true;
                } else {
                    // Show regular completion notification
                    addNotification(
                        'Quest Completed!', 
                        `You gained ${response.data.xp_gained} XP and increased your ${response.data.stat_increased} by ${response.data.stat_change.toFixed(2)}!`,
                        'success'
                    );
                }
            } catch (error) {
                console.error('Quest completion error:', error);
                addNotification('Error', 'Failed to complete quest', 'error');
            }
        };
        
        const failQuest = async (questId) => {
            try {
                const response = await axios.post(`/api/quests/${questId}/fail`);
                
                // Update dashboard
                await loadDashboard();
                
                addNotification(
                    'Quest Failed', 
                    `You lost ${response.data.xp_lost} XP and decreased your ${response.data.stat_decreased} by ${response.data.stat_change.toFixed(2)}`,
                    'error'
                );
            } catch (error) {
                console.error('Quest failure error:', error);
                addNotification('Error', 'Failed to mark quest as failed', 'error');
            }
        };
        
        const generateSampleQuest = async () => {
            try {
                const response = await axios.post('/api/generate-sample-quest', {
                    goal: 'Improve yourself'
                });
                
                // Update dashboard to show new quest
                await loadDashboard();
                
                addNotification('New Quest', 'A new quest has been generated!', 'info');
            } catch (error) {
                console.error('Quest generation error:', error);
                addNotification('Error', 'Failed to generate quest', 'error');
            }
        };
        
        const generateQuestForGoal = async (goalDescription) => {
            try {
                const response = await axios.post('/api/generate-quest', {
                    goal: goalDescription
                });
                
                // Update dashboard to show new quest
                await loadDashboard();
                
                addNotification('New Quest', `A new quest has been generated for: ${goalDescription}`, 'info');
            } catch (error) {
                console.error('Quest generation error:', error);
                addNotification('Error', 'Failed to generate quest', 'error');
            }
        };
        
        // Attribute point allocation
        const allocatePoint = async (statName) => {
            if (dashboard.level.available_points <= 0) {
                addNotification('Error', 'No attribute points available', 'error');
                return;
            }
            
            try {
                const response = await axios.post('/api/level/allocate', {
                    stat: statName,
                    points: 1
                });
                
                // Update stats and available points
                dashboard.stats = response.data.stats;
                dashboard.level.available_points = response.data.available_points;
                
                addNotification('Point Allocated', `You increased your ${statName} by 1 point!`, 'success');
            } catch (error) {
                console.error('Point allocation error:', error);
                addNotification('Error', 'Failed to allocate point', 'error');
            }
        };
        
        // Utility methods
        const formatDate = (dateString) => {
            const date = new Date(dateString);
            return date.toLocaleString([], { 
                hour: '2-digit', 
                minute: '2-digit',
                month: 'short',
                day: 'numeric'
            });
        };
        
        const calculateStatWidth = (value) => {
            // Convert stat value to percentage (assuming max value of 50 for display)
            const maxStat = 50;
            const percentage = ((value + maxStat) / (maxStat * 2)) * 100;
            return `${Math.min(100, Math.max(0, percentage))}%`;
        };
        
        const getStatBarColor = (value) => {
            if (value < 0) {
                return 'bg-red-500';
            } else if (value < 10) {
                return 'bg-yellow-500';
            } else if (value < 25) {
                return 'bg-blue-500';
            } else {
                return 'bg-green-500';
            }
        };
        
        // Auto-refresh dashboard every 60 seconds to check for new optional quests
        let refreshInterval;
        
        onMounted(async () => {
            try {
                const response = await axios.get('/api/me');
                if (response.data.user) {
                    user.value = response.data.user;
                    isAuthenticated.value = true;
                    
                    // Load dashboard data
                    await loadDashboard();
                    await loadGoals();
                    
                    // Set up auto-refresh
                    refreshInterval = setInterval(async () => {
                        if (isAuthenticated.value) {
                            await loadDashboard();
                        }
                    }, 60000); // 60 seconds
                }
            } catch (error) {
                console.error('Auth check error:', error);
                // Not authenticated, stay on login screen
            }
        });
        
        // Clean up interval on component unmount
        const beforeUnmount = () => {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
        };
        
        return {
            // Auth state
            isAuthenticated,
            authScreen,
            user,
            loginForm,
            registerForm,
            login,
            register,
            logout,
            addImprovementGoal,
            removeImprovementGoal,
            
            // App data
            dashboard,
            goals,
            newGoal,
            
            // Level up animation
            showLevelUpAnimation,
            levelUpDetails,
            
            // Methods
            loadDashboard,
            loadGoals,
            createGoal,
            deleteGoal,
            completeQuest,
            failQuest,
            generateSampleQuest,
            generateQuestForGoal,
            allocatePoint,
            
            // Utilities
            formatDate,
            calculateStatWidth,
            getStatBarColor,
            
            // Notifications
            notifications,
            addNotification,
            removeNotification
        };
    }
});

app.mount('#app');
