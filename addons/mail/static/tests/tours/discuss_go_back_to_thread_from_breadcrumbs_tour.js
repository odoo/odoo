import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_go_back_to_thread_from_breadcrumbs.js", {
    steps: () => [
        { trigger: ".o-mail-DiscussContent-threadName[title='Unread']" },
        { trigger: ".o-mail-DiscussSidebar-item:contains('general')", run: "click" },
        { trigger: "button[title='View or join channels']:not(:visible)", run: "click" },
        { trigger: ".breadcrumb-item:contains('general')", run: "click" },
        { trigger: ".o-mail-DiscussContent-threadName[title='general']" },
    ],
});
