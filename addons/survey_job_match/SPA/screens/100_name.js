/* Opening screen: who is playing. */
JM.registerScreen("name", {
    setup: function () {
        var input = JM.dom.role("name", "input");
        var error = JM.dom.role("name", "error");

        JM.dom.text(JM.dom.role("name", "title"), JM.config.name_screen_title);
        input.setAttribute("placeholder", JM.config.name_placeholder || "");

        var proceed = function () {
            JM.state.name = input.value.trim();
            if (!JM.state.name) {
                JM.dom.text(error, "Please enter your name.");
                return;
            }
            JM.dom.text(error, "");
            JM.flow.next();
        };

        JM.dom.role("name", "next").addEventListener("click", proceed);
        input.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                proceed();
            }
        });
    },

    enter: function () {
        JM.dom.text(JM.dom.role("name", "progress"), JM.flow.label());
    }
});
