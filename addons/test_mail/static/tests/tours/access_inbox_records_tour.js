import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("access_inbox_records_tour", {
    steps: () => [
        {
            trigger: ".o-mail-DiscussSystray-class .fa-comments",
            run: "click",
        },
        {
            trigger: ".o-mail-MessagingMenu-tab:has(:text('Notifications'))",
            run: "click",
        },
        {
            trigger: ".o-mail-NotificationItem:has(:text(Inaccessible Record))",
            run: "click",
        },
        {
            trigger: ".o_dialog .o-mail-Message-body:text(Message in inaccessible record)",
        },
        {
            trigger: ".o_dialog .btn-close",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSystray-class .fa-comments",
            run: "click",
        },
        {
            trigger: ".o-mail-NotificationItem:has(:text(Accessible Record))",
            run: "click",
        },
        {
            trigger: ".o_form_view:has(:text(Accessible Record))",
        },
    ],
});
