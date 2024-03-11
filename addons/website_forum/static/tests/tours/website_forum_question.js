odoo.define('website_forum.tour_forum_question', function (require) {
    'use strict';

    var tour = require("web_tour.tour");

    tour.register('forum_question', {
        test: true,
        url: '/forum/help-1',
    }, [{
        content: "Ask the question in this forum by clicking on the button.",
        trigger: '.o_forum_ask_btn',
    }, {
        content: "Give your question content.",
        trigger: 'input[name=post_name]',
        run: 'text First Question Title',
    }, {
        content: "Put your question here.",
        extra_trigger: "#wrap:not(:has(input[name=post_name]:propValue('')))",
        trigger: '.note-editable p',
        run: 'text First Question',
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
    },
    {
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
        content: "Click here to accept this answer.",
        extra_trigger: '#wrap:has(".o_wforum_validate_toggler")',
        trigger: '.o_wforum_validate_toggler[data-karma]:first',
    }, {
        content: "Congratulations! You just created and post your first question and answer.",
        trigger: '#wrap:has(".o_wforum_answer_correct")',
    }]);
});
