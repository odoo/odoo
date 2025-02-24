import { registry } from "@web/core/registry";

const answerBothQuestions = [
    {
        trigger:
            ".o-livechat-root:shadow .o-mail-Message:contains(Hello, here is a first question?)",
    },
    {
        trigger: ".o-livechat-root:shadow button:contains(Yes to first question)",
        run: "click",
    },
    {
        trigger:
            ".o-livechat-root:shadow .o-mail-Message:contains(Hello, here is a second question?)",
    },
    {
        trigger: ".o-livechat-root:shadow button:contains(No to second question)",
        run: "click",
    },
];
registry.category("web_tour.tours").add("website_livechat.chatbot_trigger_selection", {
    url: "/contactus",
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        ...answerBothQuestions,
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        ...answerBothQuestions,
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
        },
    ],
});
