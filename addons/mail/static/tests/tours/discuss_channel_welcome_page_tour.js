import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_channel_welcome_page_inviter_tour.js", {
    steps: () => [
        {
            content: "The channel creator is shown as the inviter",
            trigger: ".o-mail-WelcomePage span:text(Invited by) + div:text(Inviter Peach)",
        },
    ],
});

registry.category("web_tour.tours").add("discuss_channel_welcome_page_no_inviter_tour.js", {
    steps: () => [
        {
            content: "The public user is not shown as the inviter",
            trigger: ".o-mail-WelcomePage:has(input[name='guest_name']):not(:contains(Invited by))",
        },
    ],
});
