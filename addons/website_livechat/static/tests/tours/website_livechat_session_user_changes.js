import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_login_after_chat_start", {
    url: "/",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit Hello!",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message-content:contains('Hello!')",
            run: "click",
        },
        {
            trigger: "a:contains(Sign in)",
            run: "click",
        },
        {
            trigger: "input[name='login']",
            run: "edit admin",
        },
        {
            trigger: "input[name='password']",
            run: "edit admin",
        },
        {
            trigger: "button:contains(Log in)",
            run: "click",
        },
        {
            trigger: ".o_main_navbar",
            run() {
                window.location = "/";
            },
        },
        {
            content:
                "Livechat button is present since the old livechat session was linked to the public user, not the current user.",
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
        },
    ],
});

registry.category("web_tour.tours").add("website_livechat_logout_after_chat_start", {
    url: "/",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit Hello!",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Message-content:contains('Hello!')",
            run: "click",
        },
        {
            trigger: "header#top a:contains(Mitchell Admin)",
            run: "click",
        },
        {
            trigger: "a:contains(Logout)",
            run: "click",
        },
        {
            content:
                "Livechat button is present since the old livechat session was linked to the logged user, not the public one.",
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
        },
    ],
});
