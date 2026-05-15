# SkillTree AI

A dynamic computer science course generator powered by OpenAI GPT-4o-mini.

## Setup

1. Make sure python 3.10 + is installed.

Check with:
python --version
or
python3 --version

2. Clone Github Repo.

git clone https://github.com/kchoum/SkillTree-CPSC-254.git
cd SkillTree-CPSC-254

3. Create a virtual environment
python -m venv .venv

Activate:
Windows -
.venv\Scripts\activate
Mac/Linux
source .venv/bin/activate

4. Install dependencies
pip install -r requirements.txt

5. Add your API key to .env.
Create a file named .env in the project root folder and add this line:
OPENAI_API_KEY=your_api_key_here

Replace your_api_key_here with your actual OpenAI API key

6. Start the Flask server:
python app.py
or
python3 app.py

7. Open the Web App
http://localhost:5000

The app should now be running locally.

## Features

- **Course generation** — enter any CS subject, pick your proficiency (Beginner / Intermediate / Advanced) and rigor (Casual / Standard / Intensive)
- **Lesson viewer** — click any lesson in the sidebar to load full content: explanation, code examples, key concepts, and an exercise with hints
- **Project panels** — each module has a hands-on project with a description
- **Code feedback** — upload your project code file (.py, .js, .ts, .java, .c, .cpp, etc.) and get AI-powered review with scores, strengths, improvements, and next steps