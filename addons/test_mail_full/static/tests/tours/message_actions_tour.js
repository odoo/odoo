import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("bookmark_message_tour", {
    steps: () => [
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:not([data-bookmarked]):contains(Test Message)",
            run: "hover && click #chatterRoot:shadow [title='Bookmark']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message[data-bookmarked]:contains(Test Message)",
        },
    ],
});

registry.category("web_tour.tours").add("message_actions_tour", {
    undeterministicTour_doNotCopy: true, // Remove this key to make the tour failed. ( It removes delay between steps )
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(1)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-input",
            run: "edit New message",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer button:contains(Send):enabled",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(2)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message[data-persistent]:contains(New message)",
            run: "hover && click #chatterRoot:shadow button[title='Add a Reaction']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-QuickReactionMenu-emoji span:contains(❤️)",
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains(New message) .o-mail-MessageReaction:contains(❤️)",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(New message)",
            run: "hover && click #chatterRoot:shadow button[title='Edit']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message .o-mail-Composer-input",
            run: "edit Message content changed",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message button:contains(save)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Message content changed)",
            run: "hover && click #chatterRoot:shadow button[title='Expand']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-moreMenu",
            run: "click #chatterRoot:shadow button[name='delete']",
        },
        {
            trigger: "#chatterRoot:shadow button:contains(Delete)",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Thread .o-mail-Message:count(1)",
        },
    ],
});
