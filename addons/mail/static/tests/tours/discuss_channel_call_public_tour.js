import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_channel_call_public_tour.js", {
    test: true,
    steps: () => [
        {
            content: "The call does not start on the welcome page",
            trigger: ".o-mail-WelcomePage",
            async run() {
                await new Promise((r) => setTimeout(r, 250));
                const rtcService = odoo.__WOWL_DEBUG__.root.env.services["discuss.rtc"];
                if (rtcService?.selfSession || rtcService?.state.hasPendingRequest) {
                    console.error("The call should not have started.");
                }
            },
        },
        {
            content: "Click join",
            trigger: "button[title='Join Channel']",
            run: "click",
        },
        {
            content: "Check that the call has started",
            trigger: ".o-discuss-Call",
            run() {
                if (!odoo.__WOWL_DEBUG__.root.env.services["discuss.rtc"]?.selfSession) {
                    console.error("The call should have started.");
                }
            },
        },
    ],
});
