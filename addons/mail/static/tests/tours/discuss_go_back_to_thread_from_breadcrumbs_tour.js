import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_go_back_to_thread_from_breadcrumbs.js", {
    steps: () => [
        { trigger: ".o-mail-DiscussContent-threadName[title='Inbox']" },
        { trigger: ".o-mail-DiscussSidebar-item:text('Starred messages')", run: "click" },
        { trigger: ".o-mail-DiscussContent-threadName[title='Starred messages']" },
        { trigger: "button[title='View or join channels']:not(:visible)", run: "click" },
        { trigger: ".o_last_breadcrumb_item:text('Public Channels')" },
        { trigger: ".breadcrumb-item:text('Starred messages')", run: "click" },
        { trigger: ".o-mail-DiscussContent-threadName[title='Starred messages']" },
    ],
});
