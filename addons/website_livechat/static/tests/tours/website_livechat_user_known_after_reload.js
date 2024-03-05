import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_user_known_after_reload", {
    shadow_dom: ".o-livechat-root",
    test: true,
    steps: () => [
        {
            trigger: ".o-livechat-LivechatButton",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text Hello, I need help!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.anchor.dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", bubbles: true })
                );
            },
        },
        {
            trigger: ".o-mail-Message:contains('Hello, I need help!').o-selfAuthored ",
            run() {
                window.location.reload();
            },
        },
        {
            trigger: ".o-mail-Message:contains('Hello, I need help!').o-selfAuthored ",
            isCheck: true,
        },
    ],
});
