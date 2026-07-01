import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_go_back_to_thread_from_breadcrumbs.js", {
    steps: () => [
        { trigger: ".o-mail-DiscussContent-threadName[title='Channel A']" },
        {
            trigger:
                ".o-mail-MessagingMenuItem:has(:text('Channel B')) button[title='Channel Actions']:not(:visible)",
            run: "click",
        },
        { trigger: ".o-dropdown-item:text('Advanced Settings')", run: "click" },
        { trigger: ".breadcrumb-item:contains('Channel A')", run: "click" },
        { trigger: ".o-mail-DiscussContent-threadName[title='Channel A']" },
    ],
});
