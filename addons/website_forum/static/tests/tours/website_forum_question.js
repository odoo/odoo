/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('forum_question', {
    test: true,
    url: '/forum/help-1',
    steps: () => [
    {
        content: "Ask the question in this forum by clicking on the button.",
        trigger: '.o_wforum_ask_btn',
    }, {
        content: "Give your question content.",
        trigger: 'input[name=post_name]',
        run: 'text First Question Title',
    }, {
        content: "Put your question here.",
        extra_trigger: "#wrap:not(:has(input[name=post_name]:propValue('')))",
        trigger: '.note-editable p',
        run: 'text First Question <p>code here</p>',
    }, {
        content: "Insert tags related to your question.",
        extra_trigger: '.note-editable:not(:has(br))',
        trigger: '.select2-choices',
        run: 'text Tag',
    }, {
        content: "Click to post your question.",
        extra_trigger: "#wrap:not(:has(input[id=s2id_autogen2]:propValue('')))",
        trigger: 'button:contains("Post")',
    }, {
        content: "This page contain new created question.",
        trigger: '#wrap:has(".fa-star")',
        run: function() {}, //it's a check that page has been reloaded,
    }, {
        content: "Close modal once modal animation is done.",
        extra_trigger: 'div.modal.modal_shown',
        trigger: ".modal-header button.btn-close",
    }, {
        content: "Check that the code still exists as it was written.",
        trigger: 'div.o_wforum_post_content:contains("First Question <p>code here</p>")',
    }, {
        content: "Open dropdown to edit the post",
        trigger: 'a#dropdownMenuLink',
    }, {
        content: "Click on edit",
        trigger: 'form button:contains("Edit")',
    }, {
        content: "Check that the content is the same",
        trigger: 'div.odoo-editor-editable p:contains("First Question <p>code here</p>")',
        run: function () {}, //it's a check
    }, {
        content: "Save changes",
        trigger: 'button:contains("Save Changes")',
    }, {
        trigger: "a:contains(\"Answer\").collapsed",
        content: "Click to answer.",
        position: "bottom",
    },
    {
        content: "Put your answer here.",
        trigger: '.note-editable p',
        run: 'text First Answer',
    }, {
        content: "Click to post your answer.",
        extra_trigger: '.note-editable:not(:has(br))',
        trigger: 'button:contains("Post Answer")',
    }, {
        content: "Close modal once modal animation is done.",
        extra_trigger: 'div.modal.modal_shown',
        trigger: ".modal-header button.btn-close",
    }, {
        content: "Congratulations! You just created and post your first question and answer.",
        trigger: '.o_wforum_validate_toggler',
        isCheck: true,
    }]
});
