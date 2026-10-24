/* A free-text question: the visitor's name, their email, their phone.

   One fragment serves them all, as the choice screen does, so asking for
   another detail is a data change. Answers are stored as plain strings, which
   is how the transport tells them apart from choice answers. */
JM.registerScreen("text", {
    EMAIL: /^[^@\s]+@[^@\s]+\.[^@\s]+$/,

    setup: function () {
        JM.dom.role("text", "next").addEventListener("click", function () {
            JM.screens.text.advance();
        });
        /* No key handling here: the field has the focus, so lib/050_keys.js
           leaves plain Enter to it and only acts on Ctrl+Enter. */
    },

    advance: function () {
        var question = JM.flow.current().question;
        var error = JM.dom.role("text", "error");
        var value = JM.dom.role("text", "input").value.trim();

        if (question.required) {
            if (!value) {
                JM.dom.error(error, question.required_message
                    || "Please answer this question.");
                return;
            }
        }
        if (value) {
            if (question.validation === "email") {
                if (!JM.screens.text.EMAIL.test(value)) {
                    JM.dom.error(error, "Please enter a valid email address.");
                    return;
                }
            }
        }
        JM.state.answers[question.id] = value;
        JM.dom.error(error, "");
        JM.flow.next();
    },

    enter: function (step) {
        var question = step.question;
        var description = JM.dom.role("text", "description");
        var input = JM.dom.role("text", "input");

        JM.dom.text(JM.dom.role("text", "title"), question.title);
        JM.dom.html(description, question.description_html);
        JM.dom.show(description, !!question.description_html);
        JM.dom.error(JM.dom.role("text", "error"), "");

        input.setAttribute("placeholder", question.placeholder || "");
        input.setAttribute("type", question.validation === "email" ? "email" : "text");
        /* Restore what they typed, so Back does not lose it. */
        input.value = JM.state.answers[question.id] || "";
        input.focus();

        JM.dom.text(JM.dom.role("text", "next"),
            JM.flow.isLast() ? "Submit" : "Continue");
    }
});
