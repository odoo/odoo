import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("slide_comments", {
    steps: () => [
        { trigger: "a[href='#discuss'].active:text(Comments (31))" },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-input",
            run: "edit Test comment",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Composer-send:enabled",
            run: "click",
        },
        { trigger: "a[href='#discuss']:text(Comments (32))" },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message",
            run: "hover && click #chatterRoot:shadow .o-mail-Message [title='Expand']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-moreMenu [title='Delete']",
            run: "click",
        },
        {
            trigger: "#chatterRoot:shadow button:text(Confirm)",
            run: "click",
        },
        { trigger: "a[href='#discuss']:text(Comments (31))" },
    ],
});
