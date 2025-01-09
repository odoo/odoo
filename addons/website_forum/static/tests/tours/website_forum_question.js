import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('forum_question', {
    url: '/forum/help-1',
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
        run: "editor First Question <p>code here</p>",
    },
    {
        trigger: ".note-editable:not(:has(br))",
    },
    {
        content: "Insert tags related to your question.",
        trigger: '.o_select_menu_toggler',
        run: 'click',
    },
    {
        trigger: '.o_popover input.o_select_menu_sticky',
        run: 'edit Tag',
    },
    {
        trigger: "#wrap:not(:has(.o_popover input.o_select_menu_sticky:not(:contains(''))))",
    },
    {
        content: "Click to post your question.",
        trigger: 'button:contains("Post")',
        run: "click",
    }, {
        content: "This page contain new created question.",
        trigger: '#wrap:has(.fa-star)',
    },
    {
        trigger: ".o_wforum_question:contains(marc demo)",
    },
    {
        content: "Close modal once modal animation is done.",
        trigger: ".modal.modal_shown.show:contains(thanks for posting!) button.btn-close",
        run: "click",
    },
    {
        content: "Check that the code still exists as it was written.",
        trigger: 'div.o_wforum_post_content:contains("First Question <p>code here</p>")',
    },
    {
        content: "Open dropdown to edit the post",
        trigger: '.o_wforum_question a#dropdownMenuLink',
        run: "click",
    },
    {
        content: "Click on edit",
        trigger: '.o_wforum_question button:contains("Edit")',
        run: "click",
    },
    {
        content: "Check that the content is the same",
        trigger: 'div.odoo-editor-editable p:contains("First Question <p>code here</p>")',
    },
    {
        content: "Save changes",
        trigger: 'button:contains("Save Changes")',
        run: "click",
    },
    {
        trigger: "a:contains(\"Reply\").collapsed",
        content: "Click to reply.",
        tooltipPosition: "bottom",
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
});
