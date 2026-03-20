import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.question_selection_overlapping_answers", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Choose an option)" },
        {
            trigger: ".o-livechat-root:shadow li button:eq(0)",
            run: "click",
        },
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains(You selected not X)" },
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Choose an option)" },
        {
            trigger: ".o-livechat-root:shadow li button:eq(1)",
            run: "click",
        },
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains(You selected X)" },
        {
            trigger: ".o-livechat-root:shadow button[title='Restart Conversation']",
            run: "click",
        },
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Choose an option)" },
        {
            trigger: ".o-livechat-root:shadow li button:eq(2)",
            run: "click",
        },
        { trigger: ".o-livechat-root:shadow .o-mail-Message:contains(You selected maybe X)" },
    ],
});
