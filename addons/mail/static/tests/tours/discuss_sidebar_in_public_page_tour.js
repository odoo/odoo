import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("sidebar_in_public_page_tour", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-DiscussHeader [title='Channel 1']",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(Channel 1).o-active",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(Channel 2)",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussHeader [title='Channel 2']",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(Channel 2).o-active",
            run() {
                history.back();
            },
        },
        {
            trigger: ".o-mail-DiscussHeader [title='Channel 1']",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(Channel 1).o-active",
            run() {
                history.forward();
            },
        },
        {
            trigger: ".o-mail-DiscussHeader [title='Channel 2']",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(Channel 2).o-active",
        },
    ],
});
