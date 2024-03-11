/* @odoo-module */

import tour from "web_tour.tour";

tour.register(
    "website_livechat_login_after_chat_start",
    {
        test: true,
    },
    [
        {
            trigger: ".o_livechat_button",
            run: "click",
        },
        {
            trigger: ".o_composer_text_field",
            run: "text Hello",
        },
        {
            trigger: "input.o_composer_text_field",
            run: function () {
                $("input.o_composer_text_field").trigger(
                    $.Event("keydown", { which: $.ui.keyCode.ENTER })
                );
            },
        },
        {
            trigger: "div.o_thread_message_content > p:contains('Hello')",
        },
        {
            trigger: "a:contains(Sign in)",
            run: "click",
        },
        {
            trigger: "input[name='login']",
            run: "text admin",
        },
        {
            trigger: "input[name='password']",
            run: "text admin",
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
            trigger: ".o_livechat_button",
        },
    ]
);

tour.register(
    "website_livechat_logout_after_chat_start",
    {
        test: true,
    },
    [
        {
            trigger: ".o_livechat_button",
            run: "click",
        },
        {
            trigger: ".o_composer_text_field",
            run: "text Hello",
        },
        {
            trigger: "input.o_composer_text_field",
            run: function () {
                $("input.o_composer_text_field").trigger(
                    $.Event("keydown", { which: $.ui.keyCode.ENTER })
                );
            },
        },
        {
            trigger: "div.o_thread_message_content > p:contains('Hello')",
        },
        {
            trigger: "#top_menu a:contains(Mitchell Admin)",
            run: "click",
        },
        {
            trigger: "a:contains(Logout)",
        },
        {
            content:
                "Livechat button is present since the old livechat session was linked to the logged user, not the public one.",
            trigger: ".o_livechat_button",
        },
    ]
);
