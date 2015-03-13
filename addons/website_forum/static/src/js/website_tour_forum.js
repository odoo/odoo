odoo.define('website_forum.tour_forum', function (require) {
'use strict';

var core = require('web.core');
var Tour = require('web.Tour');

var _t = core._t;

Tour.register({
    id:   'question',
    name: _t("Create a question"),
    steps: [
        {
            title:     _t("Create a Question!"),
            content:   _t("Let's go through the first steps to create a new question."),
            popover:   { next: _t("Start Tutorial"), end: _t("Skip It") },
        },
        {
            title:     _t("Add Content"),
            element:   '#content-menu-button',
            placement: 'left',
            content:   _t("Use this <em>'Content'</em> menu to create a new forum like any other document (page, menu, products, event, ...)."),
            popover:   { fixed: true },
        },
        {
            title:     _t("New Forum"),
            element:   'a[data-action=new_forum]',
            placement: 'left',
            content:   _t("Select this menu item to create a new forum."),
            popover:   { fixed: true },
        },
        {
            title:     _t("Forum Name"),
            element:   '.modal #editor_new_forum input[type=text]',
            sampleText:'New Forum',
            placement: 'right',
            content:   _t("Enter a name for your new forum then click 'Continue'."),
        },
        {
            title:     _t("Create Forum"),
            waitNot:   ".modal #editor_new_forum input[type=text]:propValue('')",
            element:   '.modal button.btn-primary',
            placement: 'right',
            content:   _t("Click <em>Continue</em> to create the forum."),
        },
        {
            title:     _t("New Forum Created"),
            waitFor:   'body:not(.modal-open)',
            content:   _t("This page contains all the information related to the new forum."),
            popover:   { next: _t("Continue") },
        },
        {
            title:     _t("Ask a Question"),
            element:   '.btn-block a:first',
            placement: 'left',
            content:   _t("Ask the question in this forum by clicking on the button."),
        },
        {
            title:     _t("Question Title"),
            element:   'input[name=post_name]',
            sampleText:'First Question Title',
            placement: 'top',
            content:   _t("Give your question title."),
        },
        {
            title:     _t("Question"),
            waitNot:   "input[name=post_name]:propValue('')",
            element:   '.note-editable p',
            sampleText: 'First Question',
            placement: 'top',
            content:   _t("Put your question here."),
        },
        {
            title:     _t("Give Tag"),
            waitFor:   '.note-editable:not(:has(br))',
            element:   '.select2-choices',
            placement: 'top',
            content:   _t("Insert tags related to your question."),
        },
        {
            title:     _t("Post Question"),
            waitNot:   "input[id=s2id_autogen2]:propValue('Tags')",
            element:   'button:contains("Post Your Question")',
            placement: 'bottom',
            content:   _t("Click to post your question."),
        },
        {
            title:     _t("New Question Created"),
            waitFor:   'body:has(".fa-star")',
            content:   _t("This page contain new created question."),
            popover:   { next: _t("Continue") },
        },
        {
            title:     _t("Answer"),
            element:   '.note-editable p',
            sampleText: 'First Answer',
            placement: 'top',
            content:   _t("Put your answer here."),
        },
        {
            title:     _t("Post Answer"),
            waitFor:   '.note-editable:not(:has(br))',
            element:   'button:contains("Post Answer")',
            placement: 'bottom',
            content:   _t("Click to post your answer."),
        },
        {
            title:     _t("Answer Posted"),
            waitFor:   'body:has(".fa-check-circle")',
            content:   _t("This page contain new created question and its answer."),
            popover:   { next: _t("Continue") },
        },
        {
            title:     _t("Accept Answer"),
            element:   'a[data-karma="20"]:first',
            placement: 'right',
            content:   _t("Click here to accept this answer."),
        },
        {
            title:     _t("Congratulations"),
            waitFor:   'body:has(".oe_answer_true")',
            content:   _t("Congratulations! You just created and post your first question and answer."),
            popover:   { next: _t("Close Tutorial") },
        },
    ]
});

});
