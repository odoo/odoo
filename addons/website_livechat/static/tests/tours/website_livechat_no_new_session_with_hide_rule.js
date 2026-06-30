import { registry } from "@web/core/registry";
import { contains, click } from "@web/../tests/utils";

const sendFirstMessageSteps = [
    {
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "edit Hello, I need help!",
    },
    {
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "press Enter",
    },
    {
        trigger:
            ".o-livechat-root:shadow .o-mail-Thread:not([data-transient]) .o-mail-Message:contains('Hello, I need help!')",
    },
];
registry.category("web_tour.tours").add("website_livechat_no_session_with_hide_rule", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...sendFirstMessageSteps,
        {
            trigger: ".o-livechat-root:shadow [title='Close Chat Window (ESC)']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains('Yes, leave conversation')",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow p:contains('Did we correctly answer your question?')",
            async run() {
                // Use contains instead of click action to ensure negative
                // assertion is based on the correct parameters below.
                await click("button", { target: this.anchor.getRootNode(), text: "New Session" });
            },
        },
        ...sendFirstMessageSteps,
        {
            trigger: "body",
            run: () => (window.location = "/"),
            expectUnloadPage: true,
        },
        {
            trigger: ".o-livechat-root:shadow [title='Close Chat Window (ESC)']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow button:contains('Yes, leave conversation')",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow p:contains('Did we correctly answer your question?')",
            async run() {
                await contains("button", { target: this.anchor.getRootNode(), text: "Close" });
                await contains("button", {
                    target: this.anchor.getRootNode(),
                    text: "New Session",
                    count: 0,
                });
            },
        },
    ],
});
