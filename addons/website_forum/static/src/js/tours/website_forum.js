odoo.define("website_forum.tour_forum", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");

    var _t = core._t;

    tour.register("question", {
        url: "/forum/1",
    }, [{
        trigger: ".o_forum_ask_btn",
        position: "left",
        content: _t("Create a new post in this forum by clicking on the button."),
    }, {
        trigger: "input[name=post_name]",
        position: "top",
        content: _t("Give your post title."),
    }, {
        trigger: ".note-editable p",
        extra_trigger: "input[name=post_name]:not(:propValue(\"\"))",
        content: _t("Put your question here."),
        position: "bottom",
        run: "text",
    }, {
        trigger: ".select2-choices",
        extra_trigger: ".note-editable p:not(:containsExact(\"<br>\"))",
        content: _t("Insert tags related to your question."),
        position: "top",
        run: function (actions) {
            actions.auto("input[id=s2id_autogen2]");
        },
    }, {
        trigger: "button:contains(\"Post\")",
        extra_trigger: "input[id=s2id_autogen2]:not(:propValue(\"Tags\"))",
        content: _t("Click to post your question."),
        position: "bottom",
    }, {
        extra_trigger: 'div.modal.modal_shown',
        trigger: ".modal-header button.close",
        auto: true,
    }, {
        trigger: "a:contains(\"Answer\").collapsed",
        content: _t("Click to answer."),
        position: "bottom",
    }, {
        trigger: ".note-editable p",
        content: _t("Put your answer here."),
        position: "bottom",
        run: async () => {
            const wysiwyg = $('.note-editable').data('wysiwyg');
            await wysiwyg.editorHelpers.insertHtml(wysiwyg.editor, 'Test', $('.note-editable p')[0], 'INSIDE');
        },
    }, {
        trigger: "button:contains(\"Post Answer\")",
        extra_trigger: ".note-editable p:not(:containsExact(\"<br>\"))",
        content: _t("Click to post your answer."),
        run: async (actions) => {
            // There is a bug when simulating the event. As the value of the
            // textarea of the form is contained in the wysiwyg editor, the
            // textarea will be empty before clicking the first time. There is
            // a handler on the form submission to fill the textarea but we need
            // to wait for a microtask before we can get the value of the
            // wysiwyg. Because of the microtask, the textarea will not be set
            // on time. So we trigger another click on the next tick.
            actions.auto();
            setTimeout(actions.auto.bind(actions));
        }
    }, {
        extra_trigger: 'div.modal.modal_shown',
        trigger: ".modal-header button.close",
        auto: true,
    }, {
        trigger: ".o_wforum_validate_toggler[data-karma=\"20\"]:first",
        content: _t("Click here to accept this answer."),
        position: "right",
    }
    ]);
});
