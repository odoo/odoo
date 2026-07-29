import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_copy_link_tour", {
    steps: () => [
        {
            trigger: "#chatterRoot:shadow .o-mail-Message:contains(Test Message)",
            run: "hover && click #chatterRoot:shadow button[title='Expand']",
        },
        {
            trigger: "#chatterRoot:shadow .o-mail-Message-moreMenu button[name='copy-link']",
        },
    ],
});
