/* One choice question.

   This single screen serves every question in data/questions.json: the flow
   pushes one step per question and enter() repopulates the fragment. Adding
   questions is a data change, never a code change.

   Answer rows follow Survey: a label wrapping a real radio input, the text, and
   a letter badge that doubles as the keyboard shortcut. Nothing here navigates
   on its own -- Continue or Enter does. */
JM.registerScreen("question", {
    LETTERS: "ABCDEFGHIJKLMNOPQRSTUVWXYZ",

    setup: function () {
        JM.dom.role("question", "next").addEventListener("click", function () {
            JM.screens.question.advance();
        });
    },

    advance: function () {
        var question = JM.flow.current().question;
        var error = JM.dom.role("question", "error");
        if (question.required) {
            if (!JM.state.answers[question.id]) {
                JM.dom.error(error, "Please pick an answer.");
                return;
            }
        }
        JM.dom.error(error, "");
        JM.flow.next();
    },

    enter: function (step) {
        var question = step.question;
        var description = JM.dom.role("question", "description");
        var box = JM.dom.role("question", "choices");

        JM.dom.text(JM.dom.role("question", "title"), question.title);
        JM.dom.html(description, question.description_html);
        JM.dom.show(description, !!question.description_html);
        JM.dom.error(JM.dom.role("question", "error"), "");

        /* Survey turns the primary action into Submit on the last step. */
        JM.dom.text(JM.dom.role("question", "next"),
            JM.flow.isLast() ? "Submit" : "Continue");

        /* Rebuilt on every entry so going Back shows the previous selection. */
        box.replaceChildren();
        question.choices.forEach(function (choice, index) {
            box.appendChild(JM.screens.question.choiceRow(question, choice, index));
        });
    },

    choiceRow: function (question, choice, index) {
        var chosen = JM.state.answers[question.id];
        var selected = false;
        if (chosen) {
            if (chosen.id === choice.id) {
                selected = true;
            }
        }
        var letter = JM.screens.question.LETTERS.charAt(index);

        var row = document.createElement("label");
        row.className = "jm_choice";
        row.classList.toggle("jm_selected", selected);

        var input = document.createElement("input");
        input.type = "radio";
        input.name = "jm_" + question.id;
        input.value = choice.id;
        input.checked = selected;
        input.dataset.key = letter;

        var label = document.createElement("span");
        label.className = "jm_choice_label";
        label.textContent = choice.label;

        var badge = document.createElement("span");
        badge.className = "jm_key";
        badge.textContent = letter;

        input.addEventListener("change", function () {
            JM.screens.question.select(question, choice, row);
        });

        row.appendChild(input);
        row.appendChild(label);
        row.appendChild(badge);
        return row;
    },

    /* Picking an answer never navigates: the visitor moves on with Continue or
       Enter, so they can change their mind first. */
    select: function (question, choice, row) {
        JM.state.answers[question.id] = choice;
        JM.dom.error(JM.dom.role("question", "error"), "");
        Array.prototype.slice.call(row.parentNode.children).forEach(function (other) {
            other.classList.toggle("jm_selected", other === row);
        });
    }
});
