import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/utils";

registry.category("web_tour.tours").add("discuss_channel_as_guest_tour.js", {
    steps: () => [
        {
            content: "Channel secret token has been hidden on welcome page",
            trigger: ".o-mail-WelcomePage",
            run() {
                if (!window.location.pathname.startsWith("/discuss/channel")) {
                    console.error("Channel secret token is still present in URL.");
                }
            },
        },
        {
            content: "Click join",
            trigger: "button[title='Join Channel']",
            run: "click",
        },
        {
            content: "Check that we are on not in a call",
            trigger: "button[name='call']",
        },
        {
            content: "Check that we are on channel page",
            trigger: ".o-mail-Thread",
            run: "press ctrl+k",
        },
        {
            trigger: ".o_command_palette_search input",
            run: "fill @",
        },
        {
            trigger: ".o-mail-DiscussCommand",
            async run() {
                await contains(".fa-hashtag", {
                    parent: [".o-mail-DiscussCommand", { text: "Test channel" }],
                });
                await contains(".fa-user", { count: 0 });
            },
        },
    ],
});
