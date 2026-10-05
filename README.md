# Viare: AI-Powered Language Learning Bot 🤖🇮🇹

An automated Telegram bot built with **Python** and **Flask** that integrates the **OpenAI API (GPT-4o-mini)** to provide an interactive language learning ecosystem. 

This project was developed to scale language tutoring by combining passive grammar correction with active engagement routines, offering students a dynamic environment to practice Italian in real-world scenarios.

## 🚀 Core Features (The "Dual-Brain" Architecture)

### 1. Passive Grammar Tutor (Real-time Monitoring)
*   **Contextual Error Detection:** Listens to messages within the community group and processes them via the OpenAI API to find grammatical, spelling, and semantic errors.
*   **Private Feedback Loop:** To avoid public embarrassment, the bot automatically identifies the user and sends a detailed, formatted correction privately via Direct Message (DM).
*   **Zero-False-Positive Logic:** Engineered prompt logic ignores casual Portuguese chatter or 100% correct Italian sentences, triggering only when genuine linguistic correction is needed.

### 2. Active Challenge Generator (Dynamic Scheduling)
*   **Automated Daily Engagement:** Uses the `schedule` library running on a dedicated thread to generate and send unique practice challenges once a day.
*   **Weighted Randomization & AI:** Selects difficulty levels (A1 to B1), activity types, and real-world scenarios (e.g., pharmacy, train station) using weighted probabilities. This data is fed into OpenAI to generate a unique, non-repetitive prompt.
*   **State Management:** Maintains a JSON-based history log (`historico_desafios.json`) to ensure the AI never repeats the same topics in sequence.

### 3. Cloud-Ready Infrastructure
*   **Multithreading:** Operates a thread-safe architecture running the Flask Web Server (for cloud health checks and port binding on Render/Heroku), the Telegram Long-Polling service, and the Job Scheduler concurrently.

## 🛠️ Tech Stack
*   **Backend:** Python 3.x, Flask
*   **APIs:** OpenAI API (gpt-4o-mini), pyTelegramBotAPI (Telebot)
*   **Task Scheduling:** Schedule, Threading
*   **Version Control:** Git, GitHub

## ⚙️ Local Setup & Installation

**Clone the repository:**
   ```bash
   git clone [https://github.com/LiviaTalmeli/tutor-italiano.git](https://github.com/LiviaTalmeli/tutor-italiano.git)
   cd tutor-italiano
