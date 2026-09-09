import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat_info_panel_tour", {
    steps: () => [
        {
            trigger:
                ".o-mail-DiscussContent-header:has(.o-mail-DiscussContent-threadName[title='Visitor'])",
        },
        {
            trigger: ".o-mail-ActionPanel:contains(Chatbot answers)",
        },
        {
            trigger: ".o-mail-ActionPanel:contains(buy the software)",
        },
        {
            trigger: ".o-mail-ActionPanel:contains(test@example.com)",
        },
    ],
});
