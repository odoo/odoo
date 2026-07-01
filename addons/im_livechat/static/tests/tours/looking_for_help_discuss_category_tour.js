import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat.looking_for_help_discuss_category_tour", {
    steps: () => [
        {
            trigger: ".o-mail-MessagingMenu-tab:has(:text('Live Chats'))",
            run: "click",
        },
        {
            trigger: "button:text('Help Needed')",
            run: "click",
        },
        {
            trigger:
                ".o-mail-MessagingMenuItem:has(:text('Visitor Sales')) ~ .o-mail-MessagingMenuItem:has(:text('Visitor Accounting'))",
        },
        {
            trigger: ".o-mail-MessagingMenuItem:has(:text('Visitor Sales')) .o-mail-favorite",
        },
        {
            trigger:
                ".o-mail-MessagingMenuItem:has(:text('Visitor Accounting')):has(:text('Invoice SO0042 not received'))",
        },
        {
            trigger:
                ".o-mail-MessagingMenuItem:has(:text('Visitor Sales')):has(:text('Delivery delayed for PO0099'))",
        },
        {
            trigger:
                ".o-mail-MessagingMenuItem:has(:text('Visitor Accounting')):not(:has(.o-mail-favorite))",
        },
        {
            trigger: ".o-mail-MessagingMenuItem:has(:text('Visitor Accounting'))",
            run: "hover && click .o-mail-MessagingMenuItem:has(:text('Visitor Accounting')) [title='Chat Actions']",
        },
        {
            trigger:
                ".o-mail-DiscussApp-sidebar:has(.o-mail-MessagingMenuItem:has(:text('Visitor Accounting')))",
        },
        {
            trigger: "button[name='livechat-status']",
            run: "hover",
        },
        {
            trigger: ".o-livechat-LivechatStatusSelection-Label:contains(In progress)",
            run: "click",
        },
        {
            trigger:
                ".o-mail-DiscussApp-sidebar:not(:has(.o-mail-MessagingMenuItem:has(:text('Visitor Accounting'))))",
        },
    ],
});
