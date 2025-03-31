import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("star_message_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Test Message)",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Mark as Todo'] i.fa-star-o",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Test Message)",
            run: "hover #chatterRoot:shadow .o-mail-Message [title='Mark as Todo'] i.fa-star.o-mail-Message-starred",
        },
    ],
});
