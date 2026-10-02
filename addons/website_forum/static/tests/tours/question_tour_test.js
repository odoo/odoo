import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("question_tour_test", {
    steps: () => [
        {
            isActive: ["#o_wforum_forums_index_list"],
            trigger: "#o_wforum_forums_index_list a.card:first",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: 'a[href$="/ask"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "input[name=post_name]",
            content: "Give your post title.",
            run: "edit Test",
        },
        {
            trigger: `input[name=post_name]:not(:empty)`,
        },
        {
            trigger: ".note-editable p",
            content: "Put your question here.",
            run: "editor Test",
        },
        {
            trigger: `.note-editable p:not(:text(<br>))`,
        },
        {
            content: "Insert tags related to your question.",
            trigger: ".o_select_menu_input",
            run: "edit Test",
        },
        {
            content: "Select found select menu item",
            trigger: ".o_select_menu_menu .o_select_menu_item:contains('Test')",
            run: "click",
        },
        {
            content: "Close search bar",
            trigger: "body",
            run: "click",
        },
        {
            trigger: "button:contains(/^Post/)",
            content: "Click to post your question.",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_wforum_content_wrapper .h3:contains(test)",
        },
        {
            content: "Close this dialog.",
            trigger: ".modal.modal_shown.show:contains(thanks for posting!) button.btn-close",
            run: "click",
        },
        {
            trigger: "a:contains(Reply).collapsed",
            content: "Click to reply.",
            run: "click",
        },
        {
            trigger: ".note-editable p",
            content: "Put your answer here.",
            run: "editor Test",
        },
        {
            trigger: `.note-editable p:not(:text(<br>))`,
        },
        {
            trigger: 'button:contains("Post Answer")',
            content: "Click to post your answer.",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_wforum_content_wrapper .h3:contains(test)",
        },
        {
            content: "Close this dialog.",
            trigger: ".modal.modal_shown.show:contains(thanks for posting!) button.btn-close",
            run: "click",
        },
        {
            trigger: ".o_wforum_validate_toggler[data-karma]:first",
            content: "Click here to accept this answer.",
            run: "click",
        },
        {
            content: "Check edit button is there",
            trigger: "a:contains('Edit your answer')",
        },
    ],
});
