/* ============================================================
   STATE
   ============================================================ */
const state = {
  course: null,
  selectedFile: null,
};

// Read the currently checked radio value for a given name
function getRadio(name) {
  const checked = document.querySelector(`input[name="${name}"]:checked`);
  return checked ? checked.value : null;
}

/* ============================================================
   SCREEN NAVIGATION
   ============================================================ */
function showScreen(id) {
  document.querySelectorAll(".screen").forEach((s) => s.classList.remove("active"));
  document.getElementById(id).classList.add("active");
  window.scrollTo(0, 0);
}

function goToSetup()  { showScreen("screen-setup"); }
function goToCourse() { showScreen("screen-course"); }

/* ============================================================
   PILL GROUPS — removed, now using native radio inputs
   ============================================================ */

/* ============================================================
   LOADING OVERLAY
   ============================================================ */
function showLoading(text = "Thinking…") {
  document.getElementById("loading-text").textContent = text;
  document.getElementById("loading-overlay").style.display = "flex";
}
function hideLoading() {
  document.getElementById("loading-overlay").style.display = "none";
}

/* ============================================================
   SUBJECT ERROR HELPERS
   ============================================================ */
function showSubjectError(msg) {
  const input = document.getElementById("subject");
  const err   = document.getElementById("subject-error");
  input.classList.add("error");
  err.textContent = "⚠ " + msg;
  err.style.display = "flex";
  input.focus();
}

function clearSubjectError() {
  document.getElementById("subject").classList.remove("error");
  document.getElementById("subject-error").style.display = "none";
}

/* ============================================================
   SCREEN 1 → GENERATE COURSE
   ============================================================ */
async function handleGenerate() {
  const subject = document.getElementById("subject").value.trim();
  clearSubjectError();

  if (!subject) {
    showSubjectError("Please enter a subject before continuing.");
    return;
  }

  const btn = document.getElementById("generate-btn");
  btn.disabled = true;
  showLoading("Checking your subject…");

  try {
    // Step 1: validate subject
    let vData;
    try {
      const vRes = await fetch("/api/validate-subject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject }),
      });
      vData = await vRes.json();
    } catch (fetchErr) {
      throw new Error("Could not reach the server. Is it running? (" + fetchErr.message + ")");
    }

    if (!vData.valid) {
      showSubjectError(vData.message || "That doesn't look like a computer science topic. Try something like 'Binary Trees' or 'Computer Networks'.");
      return;
    }

    const normalizedSubject = vData.normalized || subject;

    // Step 2: generate course
    showLoading("Building your course outline…");
    let cData;
    try {
      const cRes = await fetch("/api/generate-course", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: normalizedSubject,
          proficiency: getRadio("proficiency"),
          rigor: getRadio("rigor"),
        }),
      });
      cData = await cRes.json();
      if (!cRes.ok) throw new Error(cData.error || "Server returned " + cRes.status);
    } catch (fetchErr) {
      throw new Error("Failed to generate course: " + fetchErr.message);
    }

    state.course = cData;
    renderCourseMap(cData);
    showScreen("screen-course");

  } catch (err) {
    showSubjectError("Something went wrong: " + err.message);
  } finally {
    hideLoading();
    btn.disabled = false;
  }
}

/* ============================================================
   SCREEN 2 — RENDER COURSE MAP
   ============================================================ */
function renderCourseMap(course) {
  document.getElementById("course-title").textContent       = course.title;
  document.getElementById("course-description").textContent = course.description;

  const map = document.getElementById("course-map");
  map.innerHTML = "";

  course.modules.forEach((mod, mi) => {
    const card = document.createElement("div");
    card.className = "module-card" + (mi === 0 ? " open" : "");

    // Header
    const header = document.createElement("div");
    header.className = "module-card-header";
    header.innerHTML = `
      <span class="module-num">Module ${mod.id}</span>
      <div style="flex:1;min-width:0">
        <div class="module-card-title" style="font-size:1.05rem;font-weight:700">${escHtml(mod.title)}</div>
        ${mod.summary ? `<div class="module-summary">${escHtml(mod.summary)}</div>` : ""}
      </div>
      <span class="module-chevron">▶</span>
    `;
    header.addEventListener("click", () => card.classList.toggle("open"));

    // Body
    const body = document.createElement("div");
    body.className = "module-card-body";

    // Lessons
    (mod.lessons || []).forEach((lesson) => {
      const row = document.createElement("div");
      row.className = "content-row";
      row.innerHTML = `
        <span class="row-icon">📖</span>
        <div class="row-text">
          <div class="row-title">${escHtml(lesson.title)}</div>
          ${lesson.objective ? `<div class="row-sub">${escHtml(lesson.objective)}</div>` : ""}
        </div>
        <span class="row-arrow">›</span>
      `;
      row.addEventListener("click", () => openLesson(mod, lesson));
      body.appendChild(row);
    });

    // Project
    if (mod.project) {
      const row = document.createElement("div");
      row.className = "content-row project-row";
      row.innerHTML = `
        <span class="row-icon">🛠</span>
        <div class="row-text">
          <div class="row-title">${escHtml(mod.project.title)}</div>
          <div class="row-sub">Project — submit your code for feedback</div>
        </div>
        <span class="row-arrow">›</span>
      `;
      row.addEventListener("click", () => openProject(mod, mod.project));
      body.appendChild(row);
    }

    card.appendChild(header);
    card.appendChild(body);
    map.appendChild(card);
  });
}

/* ============================================================
   SCREEN 3 — OPEN LESSON
   ============================================================ */
async function openLesson(mod, lesson) {
  // Set breadcrumb
  document.getElementById("lesson-breadcrumb").textContent =
    `${state.course.title}  ›  Module ${mod.id}: ${mod.title}`;

  // Show skeleton while loading
  const wrap = document.getElementById("lesson-wrap");
  wrap.innerHTML = skeletonHTML();
  showScreen("screen-lesson");
  showLoading("Loading lesson…");

  try {
    const res  = await fetch("/api/load-lesson", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        course_title:     state.course.title,
        module_title:     mod.title,
        lesson_title:     lesson.title,
        lesson_objective: lesson.objective,
        proficiency:      getRadio("proficiency"),
        rigor:            getRadio("rigor"),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Unknown error");

    renderLesson(data, wrap);
  } catch (err) {
    wrap.innerHTML = `<p style="color:var(--red);padding:2rem">Error loading lesson: ${escHtml(err.message)}</p>`;
  } finally {
    hideLoading();
  }
}

/* ============================================================
   RENDER LESSON CONTENT
   ============================================================ */
function renderLesson(lesson, container) {
  const codeHTML = (lesson.code_examples || []).map((ex) => `
    <div class="code-example">
      <p class="code-example-desc">${escHtml(ex.description)}</p>
      <div class="code-block">
        <div class="code-block-header">
          <span class="code-lang">${escHtml(ex.language)}</span>
          <button class="copy-btn" onclick="copyCode(this)">Copy</button>
        </div>
        <pre>${escHtml(ex.code)}</pre>
      </div>
    </div>
  `).join("");

  const conceptsHTML = (lesson.key_concepts || []).map((c) =>
    `<span class="concept-tag">${escHtml(c)}</span>`
  ).join("");

  const hintsHTML = (lesson.exercise?.hints || []).map((h) =>
    `<li>${escHtml(h)}</li>`
  ).join("");

  container.innerHTML = `
    <div class="lesson-content">
      <h2>${escHtml(lesson.title)}</h2>
      <div class="lesson-objective">${escHtml(lesson.objective)}</div>

      <div class="lesson-section">
        <div class="section-label">Explanation</div>
        <div class="explanation-body">${renderMarkdown(lesson.explanation || "")}</div>
      </div>

      ${codeHTML ? `
      <div class="lesson-section">
        <div class="section-label">Code Examples</div>
        ${codeHTML}
      </div>` : ""}

      ${conceptsHTML ? `
      <div class="lesson-section">
        <div class="section-label">Key Concepts</div>
        <div class="concepts-list">${conceptsHTML}</div>
      </div>` : ""}

      ${lesson.exercise ? `
      <div class="lesson-section">
        <div class="section-label">Exercise</div>
        <div class="exercise-box">
          <p class="exercise-prompt">${escHtml(lesson.exercise.prompt)}</p>
          ${hintsHTML ? `
          <button class="hints-toggle" onclick="toggleHints(this)">💡 Show Hints</button>
          <ul class="hints-list">${hintsHTML}</ul>` : ""}
          ${lesson.exercise.solution_notes ? `
          <div class="solution-notes">✅ ${escHtml(lesson.exercise.solution_notes)}</div>` : ""}
        </div>
      </div>` : ""}
    </div>
  `;
}

/* ============================================================
   SCREEN 3 — OPEN PROJECT
   ============================================================ */
function openProject(mod, project) {
  document.getElementById("lesson-breadcrumb").textContent =
    `${state.course.title}  ›  Module ${mod.id}: ${mod.title}  ›  Project`;

  const wrap = document.getElementById("lesson-wrap");
  wrap.innerHTML = renderProjectPage(project);
  showScreen("screen-lesson");

  // Wire up file drop after injecting HTML
  wireFileDrop();
}

/* ============================================================
   RENDER PROJECT PAGE (with embedded feedback panel)
   ============================================================ */
function renderProjectPage(project) {
  return `
    <div class="project-page">
      <div class="project-hero">
        <div class="project-hero-label">🛠 Project</div>
        <h2>${escHtml(project.title)}</h2>
        <p>${escHtml(project.description)}</p>
      </div>

      <div class="feedback-panel">
        <div class="feedback-panel-title">📁 Submit Your Code for Feedback</div>

        <div
          class="file-drop"
          id="file-drop"
          onclick="document.getElementById('feedback-file').click()"
        >
          <div class="file-drop-icon">📂</div>
          <p id="file-drop-text">Click to browse or drag &amp; drop your file here</p>
          <p class="file-hint">Supported: .py .js .ts .java .c .cpp .cs .go .rb .rs .txt .md</p>
        </div>
        <input
          type="file"
          id="feedback-file"
          style="display:none"
          onchange="handleFileSelect(event)"
        />

        <div class="form-group" style="margin-top:1rem;margin-bottom:0">
          <label style="font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:var(--text-muted);margin-bottom:0.5rem;display:block">
            Notes for the reviewer <span style="font-weight:400;text-transform:none">(optional)</span>
          </label>
          <textarea
            id="feedback-context"
            rows="3"
            placeholder="e.g. I'm unsure about my loop logic, or I want feedback on efficiency…"
          ></textarea>
        </div>

        <button
          class="feedback-submit-btn"
          id="feedback-btn"
          onclick="submitFeedback('${escHtml(project.description)}')"
        >
          Get Feedback
        </button>

        <div id="feedback-result" class="feedback-result"></div>
      </div>
    </div>
  `;
}

/* ============================================================
   FILE DROP WIRING (called after project page is injected)
   ============================================================ */
function wireFileDrop() {
  state.selectedFile = null;

  const drop = document.getElementById("file-drop");
  if (!drop) return;

  drop.addEventListener("dragover", (e) => {
    e.preventDefault();
    drop.classList.add("dragover");
  });
  drop.addEventListener("dragleave", () => drop.classList.remove("dragover"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  });
}

function handleFileSelect(event) {
  const file = event.target.files[0];
  if (file) setSelectedFile(file);
}

function setSelectedFile(file) {
  state.selectedFile = file;
  document.getElementById("file-drop-text").innerHTML =
    `<span class="file-selected">📄 ${escHtml(file.name)}</span>`;
}

/* ============================================================
   SUBMIT FEEDBACK
   ============================================================ */
async function submitFeedback(projectDescription) {
  if (!state.selectedFile) {
    alert("Please select a code file first.");
    return;
  }

  const btn = document.getElementById("feedback-btn");
  btn.disabled = true;
  showLoading("Reviewing your code…");

  const formData = new FormData();
  formData.append("file",                state.selectedFile);
  formData.append("proficiency",         getRadio("proficiency"));
  formData.append("context",             document.getElementById("feedback-context").value.trim());
  formData.append("project_description", projectDescription || "");

  try {
    const res  = await fetch("/api/code-feedback", {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Unknown error");

    renderFeedback(data);
  } catch (err) {
    alert("Error getting feedback: " + err.message);
  } finally {
    hideLoading();
    btn.disabled = false;
  }
}

/* ============================================================
   RENDER FEEDBACK RESULTS
   ============================================================ */
function renderFeedback(fb) {
  const result = document.getElementById("feedback-result");
  if (!result) return;

  const scoreColor = (n) => n >= 8 ? "high" : n >= 5 ? "mid" : "low";

  const improvementsHTML = (fb.improvements || []).map((imp) => `
    <div class="improvement-item">
      <p class="improvement-issue">⚠️ ${escHtml(imp.issue)}</p>
      <p class="improvement-suggestion">${escHtml(imp.suggestion)}</p>
      ${imp.example ? `<pre class="improvement-example">${escHtml(imp.example)}</pre>` : ""}
    </div>
  `).join("");

  const strengthsHTML = (fb.strengths || []).map((s) =>
    `<span class="tag-green">${escHtml(s)}</span>`
  ).join("");

  const styleHTML = (fb.style_notes || []).map((s) =>
    `<span class="tag-blue">${escHtml(s)}</span>`
  ).join("");

  const nextHTML = (fb.next_steps || []).map((s) =>
    `<span class="tag-green">${escHtml(s)}</span>`
  ).join("");

  result.innerHTML = `
    ${fb.overall ? `
    <div class="fb-section">
      <div class="fb-section-label">Overall Assessment</div>
      <div class="overall-box">${escHtml(fb.overall)}</div>
    </div>` : ""}

    ${fb.score ? `
    <div class="fb-section">
      <div class="fb-section-label">Scores</div>
      <div class="score-grid">
        <div class="score-item">
          <div class="score-label">Correctness</div>
          <div class="score-value ${scoreColor(fb.score.correctness)}">${fb.score.correctness}<span class="score-denom">/10</span></div>
        </div>
        <div class="score-item">
          <div class="score-label">Readability</div>
          <div class="score-value ${scoreColor(fb.score.readability)}">${fb.score.readability}<span class="score-denom">/10</span></div>
        </div>
        <div class="score-item">
          <div class="score-label">Efficiency</div>
          <div class="score-value ${scoreColor(fb.score.efficiency)}">${fb.score.efficiency}<span class="score-denom">/10</span></div>
        </div>
      </div>
      ${fb.score.note ? `<p class="score-note">${escHtml(fb.score.note)}</p>` : ""}
    </div>` : ""}

    ${strengthsHTML ? `
    <div class="fb-section">
      <div class="fb-section-label">Strengths</div>
      <div class="tag-list">${strengthsHTML}</div>
    </div>` : ""}

    ${improvementsHTML ? `
    <div class="fb-section">
      <div class="fb-section-label">Areas to Improve</div>
      ${improvementsHTML}
    </div>` : ""}

    ${styleHTML ? `
    <div class="fb-section">
      <div class="fb-section-label">Style &amp; Readability</div>
      <div class="tag-list">${styleHTML}</div>
    </div>` : ""}

    ${nextHTML ? `
    <div class="fb-section">
      <div class="fb-section-label">Next Steps</div>
      <div class="tag-list">${nextHTML}</div>
    </div>` : ""}
  `;

  result.scrollIntoView({ behavior: "smooth" });
}

/* ============================================================
   HINTS TOGGLE
   ============================================================ */
function toggleHints(btn) {
  const list = btn.nextElementSibling;
  list.classList.toggle("visible");
  btn.textContent = list.classList.contains("visible") ? "🙈 Hide Hints" : "💡 Show Hints";
}

/* ============================================================
   COPY CODE
   ============================================================ */
function copyCode(btn) {
  const code = btn.closest(".code-block").querySelector("pre").textContent;
  navigator.clipboard.writeText(code).then(() => {
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = "Copy"), 1500);
  });
}

/* ============================================================
   SKELETON LOADER
   ============================================================ */
function skeletonHTML() {
  return `
    <div style="padding:2rem;display:flex;flex-direction:column;gap:0">
      <div class="skeleton h2"  style="margin-bottom:1.25rem"></div>
      <div class="skeleton wide"></div>
      <div class="skeleton med"></div>
      <div class="skeleton wide" style="margin-top:1.5rem"></div>
      <div class="skeleton med"></div>
      <div class="skeleton short"></div>
      <div class="skeleton tall" style="margin-top:1.5rem"></div>
    </div>
  `;
}

/* ============================================================
   SIMPLE MARKDOWN RENDERER
   ============================================================ */
function renderMarkdown(text) {
  // Escape first, then apply markdown transforms
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Headings
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm,  "<h2>$1</h2>");
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  // List items
  html = html.replace(/^\s*[-*] (.+)$/gm, "<li>$1</li>");
  // Wrap consecutive <li> in <ul>
  html = html.replace(/(<li>[\s\S]*?<\/li>)(\n<li>[\s\S]*?<\/li>)*/g, (m) => `<ul>${m}</ul>`);
  // Paragraphs
  html = html
    .split(/\n\n+/)
    .map((block) => {
      if (/^<[hul]/.test(block.trim())) return block;
      return `<p>${block.trim()}</p>`;
    })
    .join("\n");

  return html;
}

/* ============================================================
   ESCAPE HTML
   ============================================================ */
function escHtml(str) {
  if (typeof str !== "string") return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ============================================================
   ENTER KEY ON SUBJECT INPUT
   ============================================================ */
document.getElementById("subject").addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleGenerate();
});

document.getElementById("subject").addEventListener("input", () => {
  clearSubjectError();
});
