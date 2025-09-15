import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("star_message_tour", {
    steps: () => [
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:not([data-starred]):contains(Test Message)",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Mark as Todo']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message[data-starred]",
        },
    ],
});
