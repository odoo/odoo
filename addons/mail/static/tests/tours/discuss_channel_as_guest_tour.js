import { registry } from "@web/core/registry";

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
            content: "Guest shouldn't join channel until click on 'Join Channel'",
            trigger: "body",
            run() {
                window.location.reload();
            },
        },
        {
            content: "Click join",
            trigger: "button[title='Join Channel']",
            run: "click",
        },
        {
            content: "Check that we are on channel page",
            trigger: ".o-mail-Thread",
        },
    ],
});
