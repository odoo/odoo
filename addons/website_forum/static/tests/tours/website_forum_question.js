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
        trigger: 'button:contains("Post Your Question")',
    }, {
        content: "This page contain new created question.",
        extra_trigger: '#wrap:has(".fa-star")',
        trigger: 'button[data-dismiss="modal"]',
    }, {
        content: "Put your answer here.",
        trigger: '.note-editable p',
        run: 'text First Answer',
    }, {
        content: "Click to post your answer.",
        extra_trigger: '.note-editable:not(:has(br))',
        trigger: 'button:contains("Post Answer")',
    }, {
        content: "This page contain new created question and its answer.",
        extra_trigger: '#wrap:has(".o_wforum_validate_toggler")',
        trigger: 'button[data-dismiss="modal"]',
    }, {
        content: "Click here to accept this answer.",
        trigger: '.o_wforum_validate_toggler[data-karma="20"]:first',
    }, {
        content: "Congratulations! You just created and post your first question and answer.",
        trigger: '#wrap:has(".o_wforum_answer_correct")',
    }]);
});
