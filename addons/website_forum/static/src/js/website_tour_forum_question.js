odoo.define('website_forum.tour_forum_question', function (require) {
'use strict';

var Tour = require('web.Tour');

Tour.register({
    id:   'forum_question',
    name: "try to create question",
    path: '/forum/help-1',
    mode: 'test',
    steps: [
        {
            title:     "Ask a Question",
            element:   '.btn-block a:first',
            placement: 'left',
            content:   "Ask the question in this forum by clicking on the button.",
        },
        {
            title:     "Question Title",
            element:   'input[name=post_name]',
            sampleText:'First Question Title',
            placement: 'top',
            content:   "Give your question title.",
        },
        {
            title:     "Question",
            waitNot:   "input[name=post_name]:propValue('')",
            element:   '.note-editable p',
            sampleText: 'First Question',
            placement: 'top',
            content:   "Put your question here.",
        },
        {
            title:     "Give Tag",
            waitFor:   '.note-editable:not(:has(br))',
            element:   '.select2-choices',
            sampleText:'Tag',
            placement: 'top',
            content:   "Insert tags related to your question.",
        },
        {
            title:     "Post Question",
            waitNot:   "input[id=s2id_autogen2]:propValue('')",
            element:   'button:contains("Post Your Question")',
            placement: 'bottom',
            content:   "Click to post your question.",
        },
        {
            title:     "New Question Created",
            waitFor:   'body:has(".fa-star")',
            content:   "This page contain new created question.",
            popover:   { next: "Continue" },
        },
        {
            title:     "Answer",
            element:   '.note-editable p',
            sampleText: 'First Answer',
            placement: 'top',
            content:   "Put your answer here.",
        },
        {
            title:     "Post Answer",
            waitFor:   '.note-editable:not(:has(br))',
            element:   'button:contains("Post Answer")',
            placement: 'bottom',
            content:   "Click to post your answer.",
        },
        {
            title:     "Answer Posted",
            waitFor:   'body:has(".fa-check-circle")',
            content:   "This page contain new created question and its answer.",
            popover:   { next: "Continue" },
        },
        {
            title:     "Accept Answer",
            element:   'a[data-karma="20"]:first',
            placement: 'right',
            content:   "Click here to accept this answer.",
        },
        {
            title:     "Congratulations",
            waitFor:   'body:has(".oe_answer_true")',
            content:   "Congratulations! You just created and post your first question and answer.",
            popover:   { next: "Close Tutorial" },
        },
    ]
});

});