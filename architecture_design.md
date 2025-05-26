# "Alone, I Level Up" App - Architecture Design (MVP)

## 1. Overview

The application will follow a client-server architecture. The backend will be a RESTful API built with FastAPI, responsible for all business logic, data storage, and interactions with background services. The initial frontend for MVP testing and demonstration will be a simple Single Page Application (SPA) built with Vue 3, interacting with the backend API.

Key components include:
- **Backend API (FastAPI)**: Manages core logic, data, and user interactions.
- **Database (PostgreSQL)**: Stores all persistent data (users, goals, quests, stats, etc.).
- **Background Task Queue (Celery + Redis)**: Handles scheduled tasks like daily quest generation, neglect timer checks, and weekly report generation.
- **Frontend (Vue 3 SPA)**: Provides the user interface for interacting with the app.

## 2. Backend Architecture (FastAPI)

The backend will be modular, with distinct services handling different aspects of the application.

### 2.1. Core Modules/Components:

1.  **User Management & Authentication:**
    *   Handles user registration (email/password), login (JWT-based), and potentially OAuth2 (Google).
    *   Manages user profiles and preferences.
    *   Corresponds to `Sprint 2` in `todo.md`.

2.  **Goal Management:**
    *   Allows users to Create, Read, Update, and Delete (CRUD) their personal goals.
    *   Each goal can have attributes like description and frequency.
    *   Corresponds to `Sprint 4 (Goal CRUD)` in `todo.md`.

3.  **Quest Engine:**
    *   **Quest Generation:** Generates daily quests based on user goals, difficulty, and other parameters (as per Spec 8.1). This will be a scheduled task.
    *   **Quest Lifecycle Management:** Tracks quest status (Pending, Completed, Failed) as per Spec Appendix B2.
    *   Handles manual quest completion and failure inputs from the user.
    *   Corresponds to `Sprint 4 (Quest Generation)` in `todo.md`.

4.  **XP & Stat Engine:**
    *   Calculates and applies XP gains or losses based on quest outcomes (FR-03, FR-04, FR-08, FR-09).
    *   Adjusts user stats (Strength, Intelligence, Discipline, Focus, Communication, Adaptability) based on XP changes (FR-05).
    *   Corresponds to `Sprint 3` in `todo.md`.

5.  **Title Logic Engine:**
    *   Manages the user's title ("Alone, I Level Up" / "Alone, I Level Down").
    *   Monitors stat levels (FR-06, FR-11) and user activity (neglect timer - Spec 8.3, FR-11).
    *   Handles title reversion logic (FR-07).
    *   Corresponds to `Sprint 5` in `todo.md`.

6.  **Notification Service (Basic MVP):**
    *   Handles sending notifications for new quests and reminders.
    *   For MVP, this might be simplified (e.g., console logs or basic email) before full Firebase/APNs integration.
    *   Corresponds to `Sprint 6` in `todo.md`.

7.  **Reporting Service:**
    *   Generates weekly reports summarizing user progress (XP, stats, streaks) (FR-10).
    *   Delivers reports (e.g., via email for MVP).
    *   Corresponds to `Sprint 7` in `todo.md`.

### 2.2. Key API Endpoints (Illustrative - based on Spec & todo.md):

*   **Authentication:**
    *   `POST /auth/register`
    *   `POST /auth/token` (Login)
    *   `GET /users/me` (Get current user info)
*   **Goals:**
    *   `POST /v1/goals`
    *   `GET /v1/goals`
    *   `GET /v1/goals/{goal_id}`
    *   `PUT /v1/goals/{goal_id}`
    *   `DELETE /v1/goals/{goal_id}`
*   **Quests:**
    *   `GET /v1/quests` (Get daily/pending quests)
    *   `POST /v1/quests/{quest_id}/complete`
    *   `POST /v1/quests/{quest_id}/fail`
    *   *(Internal: `/generate_quest` endpoint from `main.py` might be refactored into a service called by a scheduled job)*
*   **Stats & Dashboard:**
    *   `GET /v1/stats` (or `GET /v1/dashboard_info` including title, stats, quests)
*   **Reports:**
    *   `GET /v1/reports/latest`

### 2.3. Data Models (Pydantic for SQLModel/SQLAlchemy):

Based on `Specification Document.txt` (Section 7) and `todo.md` (Sprint 1):

*   **User:** `id`, `email`, `hashed_password`, `name` (optional), `locale`, `title`, `created_at`.
*   **Goal:** `id`, `user_id` (FK), `description`, `frequency`, `created_at`, `is_active`.
*   **Quest:** `id`, `user_id` (FK), `goal_id` (FK, optional), `text`, `due_date`, `difficulty`, `reward_xp`, `status` (e.g., pending, completed, failed), `created_at`, `completed_at` (nullable).
*   **Stat:** `id`, `user_id` (FK), `strength`, `intelligence`, `discipline`, `focus`, `communication`, `adaptability`, `last_updated`.
*   **XPEvent:** `id`, `user_id` (FK), `quest_id` (FK, nullable), `delta_xp`, `timestamp`, `reason` (e.g., quest_completion, penalty).
*   **Report:** `id`, `user_id` (FK), `week_start_date`, `content_json`, `created_at`.

### 2.4. Database:

*   **PostgreSQL:** Chosen for its relational capabilities, ACID compliance, and robustness (Spec 12).
*   **Alembic:** For database schema migrations (`todo.md`, Sprint 1).

### 2.5. Background Tasks (Celery + Redis):

*   **Daily Quest Generation:** Runs once a day to create new quests for active users and goals.
*   **Neglect Timer:** Periodically checks for user inactivity (e.g., every hour as per FR-07) to trigger title changes.
*   **Weekly Report Generation:** Runs weekly (e.g., Sunday) to compile and send reports.

## 3. Frontend Architecture (Vue 3 SPA - for MVP)

The frontend will be a lightweight SPA providing essential user interactions for the MVP.

### 3.1. Key Views/Components:

*   **Authentication Pages:** Login, Registration.
*   **Dashboard:**
    *   Displays current **Title**.
    *   Shows current **Stats** (e.g., using progress bars).
    *   Lists active/pending **Daily Quests**.
*   **Quest Management:**
    *   Allows users to mark quests as complete or failed.
*   **Goal Management:**
    *   Basic interface for users to CRUD their goals.
*   **Stats View (Simple):**
    *   A page to view current stat values (detailed history graph is FR-13, likely post-MVP).
*   **Notifications/Toasts:** For feedback on actions like XP gain/loss.

### 3.2. Interaction with Backend API:

*   Uses standard HTTP requests (e.g., via `axios` or `fetch API`) to communicate with the FastAPI backend.
*   Handles JWT for authenticated requests.

## 4. Data Flow Examples (Simplified)

1.  **User Completes a Quest:**
    *   User clicks "Complete" on a quest in Vue frontend.
    *   Frontend sends `POST /v1/quests/{quest_id}/complete` to API.
    *   Backend API: Validates request, updates Quest status to 'completed'.
    *   XP/Stat Engine: Calculates XP gain, updates User's XP and relevant Stat(s) in DB.
    *   Title Logic Engine: Checks if stat changes trigger a title update.
    *   API returns success response to frontend.
    *   Frontend updates UI (e.g., shows XP gain toast, refreshes quest list/stats).

2.  **Daily Quest Generation:**
    *   Celery scheduled task triggers Quest Generation service.
    *   Service fetches active users and their goals from DB.
    *   For each user/goal, generates new quests based on defined logic.
    *   Saves new quests to DB.
    *   (Optional for MVP basic notification) Triggers Notification Service to inform user.

3.  **Neglect Timer Check:**
    *   Celery scheduled task triggers Neglect Timer service.
    *   Service checks users for inactivity (e.g., no quests completed in 72h) from DB.
    *   If inactivity threshold met, Title Logic Engine updates user's title to "Alone, I Level Down" in DB.

## 5. Tech Stack Summary (MVP)

*   **Backend:** Python, FastAPI, SQLModel (or SQLAlchemy + Pydantic), PostgreSQL.
*   **Async Tasks:** Celery, Redis.
*   **Frontend (for testing/MVP):** JavaScript, Vue 3, Vite.
*   **Containerization:** Docker, Docker Compose (for local dev).
*   **Version Control:** Git (assumed).
*   **Initial Deployment Target (as per Sprint Plan):** fly.io, Railway, or Render (using Docker).

This architecture is designed to meet the MVP requirements outlined in the Specification Document (Appendix C) and the Sprint Plan, providing a solid foundation for future enhancements.
