import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_go_back_to_thread_from_breadcrumbs.js", {
    steps: () => [
        { trigger: ".o-mail-Discuss-threadName[title='Inbox']" },
        { trigger: ".o-mail-DiscussSidebar-item:contains(Starred)", run: "click" },
        { trigger: "button[title='View or join channels']", run: "click" },
        { trigger: ".breadcrumb-item:contains(Starred)", run: "click" },
        { trigger: ".o-mail-Discuss-threadName[title='Starred']" },
    ],
});
