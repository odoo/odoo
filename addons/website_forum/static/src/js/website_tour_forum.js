odoo.define("website_forum.tour_forum", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");
    var base = require("web_editor.base");

    var _t = core._t;

    tour.register("question", {
        url: "/",
        wait_for: base.ready(),
    }, [tour.STEPS.WEBSITE_NEW_PAGE, {
        trigger: "a[data-action=new_forum]",
        content: _t("Select this menu item to create a new forum."),
        position: "bottom",
    }, {
        trigger: "#editor_new_forum input[type=text]",
        content: _t("Enter a name for your new forum."),
        position: "right",
    }, {
        trigger: "button.btn-primary",
        extra_trigger: '.modal #editor_new_forum input[type=text]:not(:propValue(""))',
        content: _t("Click <em>Continue</em> to create the forum."),
        position: "right",
    }, {
        trigger: ".btn-block a:first",
        position: "left",
        content: _t("Ask the question in this forum by clicking on the button."),
    }, {
        trigger: "input[name=post_name]",
        position: "top",
        content: _t("Give your question title."),
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
        trigger: "button:contains(\"Post Your Question\")",
        extra_trigger: "input[id=s2id_autogen2]:not(:propValue(\"Tags\"))",
        content: _t("Click to post your question."),
        position: "bottom",
    }, {
        extra_trigger: 'div.modal.modal_shown',
        trigger: ".modal-header button.close",
        auto: true,
    }, {
        trigger: ".note-editable p",
        content: _t("Put your answer here."),
        position: "bottom",
        run: "text",
    }, {
        trigger: "button:contains(\"Post Answer\")",
        extra_trigger: ".note-editable p:not(:containsExact(\"<br>\"))",
        content: _t("Click to post your answer."),
        position: "bottom",
    }, {
        extra_trigger: 'div.modal.modal_shown',
        trigger: ".modal-header button.close",
        auto: true,
    }, {
        trigger: "a[data-karma=\"20\"]:first",
        content: _t("Click here to accept this answer."),
        position: "right",
    }]);
});
