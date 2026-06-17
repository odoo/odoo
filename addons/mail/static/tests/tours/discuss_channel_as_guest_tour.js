import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_channel_as_guest_tour.js", {
    steps: () => [
        {
            content: "Shareable invitation link is shown on welcome page",
            trigger: ".o-mail-WelcomePage",
            run() {
                if (!/^\/chat\/\d+\/[^/]+$/.test(window.location.pathname)) {
                    console.error("Invitation link is not present in URL on welcome page.");
                }
            },
        },
        {
            content: "Fill in guest name",
            trigger: "input[name='guest_name']",
            run: "edit Guest",
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
            trigger: ".o-mail-DiscussCommand:text(Test channel)",
        },
    ],
});
