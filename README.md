# SkillTree AI

A dynamic computer science course generator powered by OpenAI GPT-4o.

## Setup

1. **Add your API key** — open `.env` and replace the placeholder:
   ```
   OPENAI_API_KEY=sk-...your key here...
   ```

2. **Run the server:**
   ```
   python app.py
   ```

3. **Open your browser** at [http://localhost:5000](http://localhost:5000)

## Features

- **Course generation** — enter any CS subject, pick your proficiency (Beginner / Intermediate / Advanced) and rigor (Casual / Standard / Intensive)
- **Lesson viewer** — click any lesson in the sidebar to load full content: explanation, code examples, key concepts, and an exercise with hints
- **Project panels** — each module has a hands-on project with a description
- **Code feedback** — upload your project code file (.py, .js, .ts, .java, .c, .cpp, etc.) and get AI-powered review with scores, strengths, improvements, and next steps

## Project Structure

```
code-lesson-creator/
├── app.py          # Flask backend + OpenAI API calls
├── requirements.txt
├── .env            # Your API key (never commit this)
└── static/
    ├── index.html  # Single-page app shell
    ├── style.css   # Dark theme UI
    └── app.js      # Frontend logic
```
