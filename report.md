What and why:
Skill tree is a teaching web application for computer science students and hobbyists which uses AI to meet the users at their level. This application uses a LLM api to dynamically create a custom computer science course of the user’s choice. By taking in a prompt which describes the user’s topic of choice, and a selection of their current skill level and desired depth of the class, the application will display a custom made course of lessons and projects fitted towards the user’s needs. Skill tree not only provides lessons for the user to gain proficiency in their chosen topic but also provides a process for them to measure their progress through the project feedback system. By submitting their projects, the web application is able to automatically provide feedback on their implementation and further assist them in developing their understanding of the topic.
The challenges in designing this system is modifying the AI behavior to fit the design specifications. If the system prompts are not properly designed then the input scope will not properly support the user input pipeline of topic prompt to project file input. The system prompt is designed to communicate with the llm to strictly define which user topic inputs are correctly defined as computer science related to support this design infrastructure.

Iterations:

Equation to measure metrics
Total score = (0.5×Topic Accuracy) + (0.5×Feedback Quality)

V1: 
Change: First prompt change after baseline implementation of application. Improve topic selection accuracy by adding “game theory” rule and improves project feedback quality. Prompt design was changed to reject non-computer science related topics.

Motivating example: In the baseline implementation the prompt was accepting broad user input like the “math” or “logic” test cases, which does not follow the design specifications and infrastructure of code focused lessons and projects. Additionally, project feedback was often insufficiently detailed or in depth as can be seen in all baseline tests on all project test samples.

Delta: 
Baseline score = (0.5×87.5) + (0.5×92)  = 89.75
V1 Score = (0.5×90) + (0.5×97.7)  = 93.85
Delta = New Score - Old Score = 4.1

Conclusion: As expected, increased rule additions to the prompt design lead to accuracy and quality increases. Next, we will see whether broad rules can be implemented to solve failures in the specific fail states in the eval.

V2:
Change: Add rules to more accurately cover user behavior which may use informal computer science terms while adding specific rejection filtering rules to increase accuracy. Also experiment with project feedback prompts by adding more detailed role playing instructions and broader rules.
Motivating example: Some vague tests case terms like “data” and “architecture” were still being validated so added more specific cs related ruling to catch broad cases. There is also room for improvement in the feedback quality metric as there were still some potential quality issues in things like inclusion of technical terms.

Delta:
V1 Score = (0.5×90) + (0.5×97.7)  = 93.85
V2 Score = (0.5×100) + (0.5×91.95)  = 95.975
Delta = New Score - Old Score = 2.125

Conclusion: Narrowing rules to fit the desired filtering results is very effective in improving the llm’s ability to achieve more accurate results. At the same time, in the case of the feedback quality metric, the less focused prompts degraded the performance. Combine all successful prompting strategies in v1 and v2 for v3.

V3:
Change: No changes needed for topic validation prompts. Change feedback system and user prompt design to target term limits and forbidden praise sub-metrics.
Motivating example: No changes needed for validation prompts as the v2 prompt design scored 100. V1 design was more successful than v2 in quality feedback metric so went back and targeted technical term limits and forbidden praise performance blockers.

Delta:
V2 Score = (0.5×100) + (0.5×91.95)  = 95.975
V3 Score = (0.5×100) + (0.5×90.80)  = 95.4
Delta = New Score - Old Score = -0.575

Conclusion: As you implement necessary prompt changes you may need to modify evaluation metrics to more accurately measure new design requirements as you iterate. A small decrease in one metric is understandable in a metric that is difficult to objectively measure like quality.

Code walkthrough: 
For this code walkthrough the user will be generating a course based on Linked Lists. The user begins their user actions on the main topic input screen. They will input “Linked Lists” into the query, select “Intermediate” as their skill level, and select “standard” as their course rigor. They then click “build my course”, activating the generateCourse function(index, 527). This then sends a “validate subject” request (index, 541) with “Linked Lists” as the subject. App.py receives this request on (app.py,53) , proceeding to build a system prompt to identify whether or not it is a valid cs topic. In this case the model returns true, allowing the index to continue with “generate course” (index,555). App.py at line 144 looks up the course specs table at line 131, giving a total of 7 modules for intermediate skill level and course rigor. The user prompt at line 169 then instructs the model to produce 4 lesson modules and 3 project modules, with a fully defined json schema. This returns a course object to be shown based on showscreen(index, 578). The user now sees 7 collapsed modules as their collapsed modules. They open the module and click the first lesson row “What is a linked list?”. ShowScreen(‘screen-lesson’) is called (index, 763) and the renderLesson (index, 804), runs to build the lesson html, showing a thorough lesson on the topic with explanations and code examples. The user returns to the course screen and repeats the same process with a project module, running fetchproject(index, 605), then load_project(app.py,315), to generate a full project brief, and then back to openProject(index, 700). The user then attempts the project with a file ready for review. In the same project screen, they drop the file into the file drop area, and types a note into the feedback notes area saying “they are not sure if it is implemented correctly. SubmitFeedback (index, 980) is run, sends a formdata object to code_feedback (app.py, 381), validates the extension, uses the model to create feedback, and sends back a feedback json object to be rendered with renderfeedback(index, 1000).
A design decision which I considered and rejected was to include a separate grading and feedback assistance option for the project file submission functions. I realized that through the llms ability to parse the feedback notes text prompt of the user, I could combine the functions of grading and assistance into one element.

AI disclosure and safety:
Kiro was used extensively in the development of Skill Tree including prompt design and user interface/experience. Early on in the apps development Kiro failed to correctly implement screen transitions with user input, causing a block in the user experience pipeline. As attempts to force the AI assistant to create a new screen transition were not working, I instead worked with the ai to work backwards to find the issue causing this block, creating tests to find out whether there were api call issues or if it was an infrastructural issue. Additionally the assistant failed to properly understand the context of my development prompts sometimes and created incomplete or nonfunctional implementations of features. This showed up in my implementation of project feedback, where it was grading the submitted file in a vacuum without considering the projects requirements or user feedback notes. I worked with the assistant to modify the prompt to strictly stick to the provided context of the self provided requirements and user input to recover.
As there are many different points in which the user themselves is providing text or file input to the system, the risk of prompt injection exists. In the code-feedback route that was described in the code walkthrough uses the uploaded file content to place directly into the ai prompt, a malicious submission is possible. Though mitigation was not expressly required to be added, prompt engineering which tells the model to not trust the user inputs, not running any instructions and only reviewing them is a way in which it could be mitigated.
