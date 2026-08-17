/* Welcome screen, as Survey opens: the title, the pitch, and one button.
   It is not a step you answer, so it does not count toward progress. */
JM.registerScreen("start", {
    counted: false,

    setup: function () {
        JM.dom.text(JM.dom.role("start", "title"), JM.config.title);
        JM.dom.text(JM.dom.role("start", "description"), JM.config.description);

        var button = JM.dom.role("start", "next");
        JM.dom.text(button, JM.config.start_label || "Start Survey");
        button.addEventListener("click", function () {
            JM.flow.next();
        });
    },

    advance: function () {
        JM.flow.next();
    }
});
