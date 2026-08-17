/* One choice question.

   This single screen serves every question in data/questions.json: the flow
   pushes one step per question and enter() repopulates the fragment. Adding
   questions is a data change, never a code change. */
JM.registerScreen("question", {
    setup: function () {
        JM.dom.role("question", "back").addEventListener("click", function () {
            JM.flow.back();
        });
        JM.dom.role("question", "next").addEventListener("click", function () {
            var question = JM.flow.current().question;
            if (question.required) {
                if (!JM.state.answers[question.id]) {
                    JM.dom.text(JM.dom.role("question", "error"),
                        "Please pick an answer.");
                    return;
                }
            }
            JM.dom.text(JM.dom.role("question", "error"), "");
            JM.flow.next();
        });
    },

    enter: function (step) {
        var question = step.question;
        var description = JM.dom.role("question", "description");
        var box = JM.dom.role("question", "choices");

        JM.dom.text(JM.dom.role("question", "progress"), JM.flow.label());
        JM.dom.text(JM.dom.role("question", "title"), question.title);
        JM.dom.text(description, question.description);
        JM.dom.show(description, !!question.description);
        JM.dom.text(JM.dom.role("question", "error"), "");

        /* Rebuilt on every entry so going Back shows the previous selection. */
        box.replaceChildren();
        question.choices.forEach(function (choice) {
            box.appendChild(JM.screens.question.choiceButton(question, choice));
        });
    },

    choiceButton: function (question, choice) {
        var chosen = JM.state.answers[question.id];
        var pressed = false;
        if (chosen) {
            if (chosen.id === choice.id) {
                pressed = true;
            }
        }

        var button = document.createElement("button");
        button.type = "button";
        button.className = "jm_choice";
        button.dataset.choice = choice.id;
        button.textContent = choice.label;
        button.setAttribute("aria-pressed", String(pressed));
        button.addEventListener("click", function () {
            JM.state.answers[question.id] = choice;
            JM.dom.text(JM.dom.role("question", "error"), "");
            Array.prototype.slice.call(button.parentNode.children)
                .forEach(function (other) {
                    other.setAttribute("aria-pressed", String(other === button));
                });
        });
        return button;
    }
});
