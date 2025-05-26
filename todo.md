# Todo List for "Alone, I Level Up" App MVP

## Phase 1: Backend Development (FastAPI & SQLModel)

### Sprint 0: Setup (Completed by User/Initial State)
- [ ] Set up mono-repo (structure for backend/frontend) - *Assuming a simplified structure for now.*
- [ ] Initialize CI pipeline (GitHub Actions with pytest + lint) - *Skipping for now, can be added later if requested.*

### Sprint 1: Data Model and Database Setup
- [ ] Design final ERD (based on spec and sprint plan).
- [ ] Define Pydantic models for all entities (Users, Goals, Quests, XP_Events, Stats, Reports) based on `Specification Document.txt`.
- [ ] Set up PostgreSQL database.
- [ ] Implement Alembic for database migrations.
- [ ] Create initial database schema based on models.

### Sprint 2: Authentication and User Management
- [ ] Implement user registration (email/password).
- [ ] Implement user login (JWT-based).
- [ ] Implement OAuth2 for Google login (optional, as per spec FR-15, but good for MVP).
- [ ] Create API endpoints for user management (e.g., `/users/me`, `/auth/token`).
- [ ] Seed demo user fixtures for testing.

### Sprint 3: Core XP/Stat Engine
- [X] Implement logic for XP and stat adjustments upon quest completion/failure (FR-03, FR-04, FR-05, FR-08, FR-09) - Refactored for ORM.
- [X] Create API endpoint for marking quests as complete/failed (e.g., `POST /v1/quests/{quest_id}/complete`, `POST /v1/quests/{quest_id}/fail`) - Refactored for ORM and syntax corrected.
- [ ] Implement stat calculation (e.g., 100 XP = +1 stat).
- [ ] Ensure unit tests cover edge cases (negative stats, rollbacks).

### Sprint 4: Quest Management and Generation
- [ ] Implement Goal CRUD operations (FR-02) (e.g., `POST /v1/goals`, `GET /v1/goals`, `PUT /v1/goals/{goal_id}`, `DELETE /v1/goals/{goal_id}`).
- [ ] Refine quest generation logic (FR-02, FR-04, Spec 8.1): daily quests per goal, difficulty, reward XP, due dates.
    - Modify existing `/generate_quest` or create a new internal service.
- [ ] Implement a mechanism to generate daily quests (e.g., a scheduled job or triggered on user login if no quests for the day).
- [ ] Create API endpoints for fetching quests (e.g., `GET /v1/quests`).

### Sprint 5: Title Logic and Neglect Timer
- [ ] Implement logic for Title change to "Alone, I Level Down" if any stat < 0 (FR-06, FR-11, Spec Appendix B1).
- [ ] Implement logic for Title change due to 72h inactivity (neglect timer) (Spec 8.3, FR-11, Spec Appendix B1).
- [ ] Implement logic for Title reverting to "Alone, I Level Up" (FR-07, Spec Appendix B1).
- [ ] Implement a background job/scheduled task to check for inactivity and stat conditions (FR-07 System auto-evaluates neglect timer).
- [ ] Create API endpoint to get current title and stats (e.g., `GET /v1/dashboard_info` or extend `GET /v1/stats`).

### Sprint 6: Notifications (Basic)
- [ ] Set up a basic notification mechanism (e.g., logging to console or simple email for now, actual push notifications are complex for MVP without Firebase/APNs setup).
- [ ] Implement notifications for new daily quests (Spec 10).
- [ ] Implement notifications for mid-day reminders if quests are incomplete (Spec 10).

### Sprint 7: Weekly Reports (Basic)
- [ ] Implement logic to generate a weekly summary (XP earned/lost, stat deltas, streaks) (FR-10).
- [ ] Create an API endpoint to fetch the latest weekly report (e.g., `GET /v1/reports/latest`).
- [ ] Implement sending weekly report via email (basic, can use a simple SMTP library for now).

## Phase 2: Basic Frontend (Vue 3 SPA - as per Sprint Plan suggestion for testing)

### Sprint 8: Thin Frontend Implementation
- [ ] Set up a basic Vue 3 + Vite SPA.
- [ ] Implement a simple dashboard view: display Title, stats bars, and current quest list.
- [ ] Implement functionality to mark quests as complete/failed (calling backend API).
- [ ] Display toasts/notifications for XP gains/losses.
- [ ] Implement basic user login/registration forms.
- [ ] Implement a view for goal management.

## Phase 3: Polish and Deployment Prep

### Sprint 9: Polish & Beta Deploy
- [ ] Implement basic error logging (e.g., Sentry or just file-based logging).
- [ ] Set up environment configurations (dev, prod).
- [ ] Dockerize the FastAPI backend.
- [ ] Dockerize the Vue frontend.
- [ ] Create Docker Compose for local development.
- [ ] Prepare for deployment (e.g., to fly.io, Railway, or Render as suggested).

### Buffer / Hardening
- [ ] Perform basic testing of all features.
- [ ] Address any critical bugs found.

This todo list is based on the MVP scope outlined in the Specification Document (Appendix C) and the Sprint Plan. Some items like full CI/CD, advanced push notifications, and specific cloud deployments are simplified for initial development but can be expanded later.
