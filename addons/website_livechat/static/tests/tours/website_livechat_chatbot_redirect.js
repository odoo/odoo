/* @odoo-module */

import tour from "web_tour.tour";

tour.register("website_livechat.chatbot_redirect", { test: true }, [
    {
        trigger: ".o_livechat_button",
    },
    {
        trigger: ".o_thread_message_content:contains(Hello, were do you want to go?)",
    },
    {
        trigger: ".o_livechat_chatbot_stepAnswer:contains(Go to the #chatbot-redirect anchor)",
    },
    {
        trigger: ".o_thread_message_content:contains(Tadam, we are on the page you asked for!)",
        run() {
            const url = new URL(location.href);
            if (url.pathname !== "/" || url.hash !== "#chatbot-redirect") {
                throw new Error("Chatbot should have redirected to the #chatbot-redirect anchor.");
            }
        },
    },
    {
        trigger: ".o_livechat_chatbot_restart",
    },
    {
        trigger: ".o_livechat_chatbot_stepAnswer:contains(Go to the /chabtot-redirect page)",
    },
    {
        trigger:
            ".o_thread_message_content:contains(Tadam, we are on the page you asked for!):eq(1)",
        run() {
            const url = new URL(location.href);
            if (url.pathname !== "/chatbot-redirect") {
                throw new Error("Chatbot should have redirected to the /chatbot-redirect page.");
            }
        },
    },
]);
