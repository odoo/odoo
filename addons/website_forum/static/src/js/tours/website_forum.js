odoo.define("website_forum.tour_forum", function (require) {
    "use strict";

    var core = require("web.core");
    const wTourUtils = require('website.tour_utils');

    var _t = core._t;

    wTourUtils.registerBackendAndFrontendTour("question", {
        url: '/forum/1',
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
        trigger: ".modal-header button.btn-close",
        auto: true,
    },
    {
        trigger: "a:contains(\"Answer\").collapsed",
        content: _t("Click to answer."),
        position: "bottom",
    },
    {
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
        trigger: ".modal-header button.btn-close",
        auto: true,
    }, {
        trigger: ".o_wforum_validate_toggler[data-karma]:first",
        content: _t("Click here to accept this answer."),
        position: "right",
    }]);
});
