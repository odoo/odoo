import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

registry.category("web_tour.tours").add("website_helpdesk_forum_tour", {
    url: "/forum/help-1",
    steps: () => [
        {
            content: "Ask the question in this forum by clicking on the button.",
            trigger: ".o_wforum_ask_btn",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: "input[name=post_name]",
            content: _t("Give your post title."),
            run: "edit Test",
        },
        {
            content: "Put your question here.",
            trigger: ".note-editable p",
            run: "editor First Question <p>code here</p>",
        },
        {
            trigger: ".note-editable p:not(:has(br))",
        },
        {
            trigger: ".o_select_menu_toggler",
            content: _t("Insert tags related to your question."),
            run: "click",
        },
        {
            trigger: ".o_select_menu_sticky",
            run: "edit Test",
        },
        {
            content: "Select found select menu item",
            trigger: ".o_popover.o_select_menu_menu",
            run: "click",
        },
        {
            trigger: "button:contains(/^Post/)",
            content: _t("Click to post your question."),
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_wforum_question:contains(test user)",
        },
        {
            trigger: ".modal.modal_shown.show:contains(thanks for posting!) button.btn-close",
            run: "click",
        },
        {
            trigger: "a[id=dropdownMenuLink]",
            run: "click",
        },
        {
            trigger: ".create_ticket_forum",
            run: "click",
        },
        {
            trigger: "input[id=ticketTitle]",
            content: _t("Give your post title."),
            run: "edit Helpdesk Ticket(Test)",
        },
        {
            trigger: "button:contains(/^Create Ticket/)",
            run: "click",
        },
    ],
});
