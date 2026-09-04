import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("question_tour", {
    steps: () => [
        {
            isActive: ["auto", "#o_wforum_forums_index_list"],
            trigger: "#o_wforum_forums_index_list a.card:first",
            run: "click",
            expectUnloadPage: true,
        },
        {
            isActive: ["manual", "#o_wforum_forums_index_list"],
            trigger: "#o_wforum_forums_index_list a.card:first",
            tooltipPosition: "bottom",
            content: _t("Select a forum to post your question in."),
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: 'a[href$="/ask"]',
            run: "click",
            expectUnloadPage: true,
        },
        {
            isActive: ["manual"],
            trigger: 'a[href$="/ask"]',
            tooltipPosition: "left",
            content: _t("Create a new post in this forum by clicking on the button."),
            run: "click",
        },
        {
            trigger: "input[name=post_name]",
            tooltipPosition: "top",
            content: _t("Give your post title."),
            run: "edit Test",
        },
        {
            trigger: `input[name=post_name]:not(:empty)`,
        },
        {
            trigger: ".note-editable p",
            content: _t("Put your question here."),
            run: "editor Test",
        },
        {
            trigger: `.note-editable p:not(:text(<br>))`,
        },
        {
            content: _t("Insert tags related to your question."),
            trigger: ".o_select_menu_input",
            tooltipPosition: "top",
            run: "edit Test",
        },
        {
            content: _t("Select found select menu item"),
            trigger: ".o_select_menu_menu .o_select_menu_item:contains('Test')",
            run: "click",
        },
        {
            content: _t("Close search bar"),
            trigger: "body",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: "button:contains(/^Post/)",
            content: _t("Click to post your question."),
            run: "click",
            expectUnloadPage: true,
        },
        {
            isActive: ["manual"],
            trigger: "button:contains(/^Post/)",
            content: _t("Click to post your question."),
            run: "click",
        },
        {
            trigger: ".o_wforum_content_wrapper .h3:contains(test)",
        },
        {
            content: _t("Close this dialog."),
            trigger: ".modal.modal_shown.show:contains(thanks for posting!) button.btn-close",
            run: "click",
        },
        {
            trigger: "a:contains(Reply).collapsed",
            content: _t("Click to reply."),
            run: "click",
        },
        {
            trigger: ".note-editable p",
            content: _t("Put your answer here."),
            run: "editor Test",
        },
        {
            trigger: `.note-editable p:not(:text(<br>))`,
        },
        {
            isActive: ["auto"],
            trigger: 'button:contains("Post Answer")',
            content: _t("Click to post your answer."),
            run: "click",
            expectUnloadPage: true,
        },
        {
            isActive: ["manual"],
            trigger: 'button:contains("Post Answer")',
            content: _t("Click to post your answer."),
            run: "click",
        },
        {
            trigger: ".o_wforum_content_wrapper .h3:contains(test)",
        },
        {
            content: _t("Close this dialog."),
            trigger: ".modal.modal_shown.show:contains(thanks for posting!) button.btn-close",
            run: "click",
        },
        {
            trigger: ".o_wforum_validate_toggler[data-karma]:first",
            content: _t("Click here to accept this answer."),
            tooltipPosition: "right",
            run: "click",
        },
        {
            content: _t("Check edit button is there"),
            trigger: "a:contains('Edit your answer')",
        },
    ],
});
