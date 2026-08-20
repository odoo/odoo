import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("sidebar_in_public_page_tour", {
    steps: () => [
        {
            trigger: ".o-mail-DiscussContent-header [title='Channel 1']",
        },
        {
            trigger: ".o-mail-NotificationItem.o-active:has(:text('Channel 1'))",
        },
        {
            trigger: ".o-mail-NotificationItem:has(:text('Channel 2'))",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussContent-header [title='Channel 2']",
        },
        {
            trigger: ".o-mail-NotificationItem.o-active:has(:text('Channel 2'))",
            run() {
                history.back();
            },
        },
        {
            trigger: ".o-mail-DiscussContent-header [title='Channel 1']",
        },
        {
            trigger: ".o-mail-NotificationItem.o-active:has(:text('Channel 1'))",
            run() {
                history.forward();
            },
        },
        {
            trigger: ".o-mail-DiscussContent-header [title='Channel 2']",
        },
        {
            trigger: ".o-mail-NotificationItem.o-active:has(:text('Channel 2'))",
        },
        {
            content: "Open channel actions",
            trigger:
                ".o-mail-MessagingMenuItem:has(.o-mail-NotificationItem.o-active:has(:text('Channel 2')))",
            run: "hover && click [title='Channel Actions']",
        },
        {
            trigger: ".o-dropdown-item:contains('Invite People')",
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("public_page_as_non_member_tour", {
    steps: () => [
        {
            trigger: ".o-mail-DiscussContent-header [title='Channel 2']",
        },
        {
            trigger: ".o-mail-Discuss:not(:has(.o-mail-MessagingMenu))",
        },
        {
            trigger: ".o-mail-MessagingMenu-navbar:not(:has(.o-mail-MessagingMenu-tab.active))",
        },
        {
            trigger: ".o-mail-MessagingMenu-tab[data-id='channel']",
            run: "click",
        },
        {
            trigger: ".o-mail-MessagingMenu-tab.active[data-id='channel']",
        },
        {
            trigger: ".o-mail-MessagingMenu .o-mail-NotificationItem:has(:text('Channel 1'))",
        },
    ],
});
