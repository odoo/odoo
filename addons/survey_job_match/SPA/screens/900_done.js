/* Closing screen: saves the run, then reports what happened.

   Entering this screen is what triggers the write, so the flow has no separate
   submit step. A failure keeps the visitor here with a retry button rather than
   losing their answers. */
JM.registerScreen("done", {
    setup: function () {
        JM.dom.role("done", "retry").addEventListener("click", function () {
            JM.screens.done.send();
        });
    },

    enter: function () {
        JM.screens.done.send();
    },

    send: function () {
        var heading = JM.dom.role("done", "heading");
        var detail = JM.dom.role("done", "detail");
        var error = JM.dom.role("done", "error");
        var actions = JM.dom.role("done", "actions");

        JM.dom.text(heading, "Saving your answers...");
        JM.dom.text(detail, "");
        JM.dom.text(error, "");
        JM.dom.show(actions, false);

        var failed = function (message) {
            JM.dom.text(heading, "We could not save your answers");
            JM.dom.text(error, message);
            JM.dom.show(actions, true);
        };

        JM.api.save().then(function (result) {
            if (result.id) {
                var suffix = "";
                if (result.mock) {
                    suffix = " -- dev preview, nothing was saved";
                }
                JM.dom.text(heading, "Thanks, " + JM.state.name + "!");
                JM.dom.text(detail,
                    "Saved as " + JM.config.model + " #" + result.id + suffix);
                return;
            }
            failed("Could not save: " + JM.api.errorOf(result));
        }).catch(function (problem) {
            failed("Network error: " + problem.message);
        });
    }
});
