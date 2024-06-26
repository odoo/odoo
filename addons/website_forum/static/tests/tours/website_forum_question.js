/** @odoo-module **/

import { registry } from "@web/core/registry";

const tourForumQuestion = {
    test: true,
    steps: () => [
    {
        content: "Ask the question in this forum by clicking on the button.",
        trigger: '.o_wforum_ask_btn',
        run: "click",
    }, {
        content: "Give your question content.",
        trigger: 'input[name=post_name]',
        run: "edit First Question Title",
    },
    {
        trigger: "#wrap:not(:has(input[name=post_name]:value('')))",
    },
    {
        content: "Put your question here.",
        trigger: '.note-editable p',
        run: "editor First Question",
    },
    {
        trigger: ".note-editable:not(:has(br))",
    },
    {
        content: "Insert tags related to your question.",
        trigger: '.select2-choices',
        run: "editor Tag",
    },
    {
        trigger: "#wrap:not(:has(input[id=s2id_autogen2]:value('')))",
    },
    {
        content: "Click to post your question.",
        trigger: 'button:contains("Post")',
        run: "click",
    },
    {
        content: "Close modal once modal animation is done.",
        trigger: ".modal .modal-header button.btn-close",
        run: "click",
    }, {
        content: "This page contain new created question.",
        trigger: '.o_wforum_post_content:contains("First Question")',
    },
    {
        trigger: "a:contains(\"Reply\").collapsed",
        content: "Click to reply.",
        position: "bottom",
        run: "click",
    },
    {
        content: "Put your answer here.",
        trigger: '.note-editable p',
        run: "editor First Answer",
    },
    {
        trigger: ".note-editable:not(:has(br))",
    },
    {
        content: "Click to post your answer.",
        trigger: 'button:contains("Post Answer")',
        run: "click",
    },
    {
        content: "Close modal once modal animation is done.",
        trigger: ".modal .modal-header button.btn-close",
        run: "click",
    }, {
        content: "Congratulations! You just created and post your first question and answer.",
        trigger: '.o_wforum_validate_toggler',
    }]
}

registry.category("web_tour.tours").add('forum_question', {
    ...tourForumQuestion,
    url: '/forum/help-1',
});

registry.category("web_tour.tours").add('forum_question_embed', {
    ...tourForumQuestion,
    url: '/forum/embed/help-1',
});
