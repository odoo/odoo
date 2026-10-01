import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_livechat.chatbot_new_session_tour", {
    steps: () => [
        {
            content: "Open the livechat, which starts the chatbot script",
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            content: "The first welcome step is posted",
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Hello, I am a bot!)",
        },
        {
            content: "The last welcome step asks a question",
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(What do you want to do?)",
        },
        {
            content: "Answer the question of the welcome step",
            trigger: ".o-livechat-root:shadow button:contains(Tell me a joke)",
            run: "click",
        },
        {
            content: "The chatbot goes on with the next step",
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Knock knock)",
        },
        {
            content: "Close the chat window to leave the session",
            trigger: ".o-livechat-root:shadow button[title='Close Chat Window (ESC)']",
            run: "click",
        },
        {
            content: "Confirm that the session has to be left",
            trigger: ".o-livechat-root:shadow button:contains(Yes, leave conversation)",
            run: "click",
        },
        {
            content: "The feedback panel of the ended session is displayed",
            trigger: ".o-livechat-root:shadow div:contains(Did we correctly answer your question?)",
        },
        {
            content: "Start a brand new session, which replays the welcome steps",
            trigger: ".o-livechat-root:shadow button:contains(New Session)",
            run: "click",
        },
        {
            content: "The first welcome step is posted again",
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Hello, I am a bot!)",
        },
        {
            content:
                "The question of the welcome step is asked again: it was completed during the " +
                "previous session, but it must not be considered completed in this one",
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(What do you want to do?)",
        },
        {
            content: "The question of the welcome step can be answered again",
            trigger: ".o-livechat-root:shadow button:contains(Tell me a joke)",
            run: "click",
        },
        {
            content: "The chatbot goes on with the next step",
            trigger: ".o-livechat-root:shadow .o-mail-Message:contains(Knock knock)",
        },
    ],
});
