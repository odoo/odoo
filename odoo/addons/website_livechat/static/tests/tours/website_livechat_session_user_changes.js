/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat_login_after_chat_start", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: ".o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text Hello!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: function () {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: ".o-mail-Message-content:contains('Hello!')",
        },
        {
            trigger: "a:contains(Sign in)",
            run: "click",
            shadow_dom: false,
        },
        {
            trigger: "input[name='login']",
            run: "text admin",
            shadow_dom: false,
        },
        {
            trigger: "input[name='password']",
            run: "text admin",
            shadow_dom: false,
        },
        {
            trigger: "button:contains(Log in)",
            run: "click",
            shadow_dom: false,
        },
        {
            trigger: ".o_main_navbar",
            shadow_dom: false,
            run() {
                window.location = "/";
            },
        },
        {
            content:
                "Livechat button is present since the old livechat session was linked to the public user, not the current user.",
            trigger: ".o-livechat-LivechatButton",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("website_livechat_logout_after_chat_start", {
    test: true,
    url: "/",
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: ".o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text Hello!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run: function () {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: ".o-mail-Message-content:contains('Hello!')",
        },
        {
            trigger: "header#top a:contains(Mitchell Admin)",
            run: "click",
            shadow_dom: false,
        },
        {
            trigger: "a:contains(Logout)",
            shadow_dom: false,
        },
        {
            content:
                "Livechat button is present since the old livechat session was linked to the logged user, not the public one.",
            trigger: ".o-livechat-LivechatButton",
            isCheck: true,
        },
    ],
});
