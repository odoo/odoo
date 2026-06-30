import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_mention_suggestions_group_restricted_channel.js", {
    steps: () => [
        { trigger: ".o-mail-DiscussContent-threadName[title='R&D Channel']" },
        { trigger: ".o-mail-Composer-input", run: "edit @" },
        { trigger: ".o-mail-Composer-suggestion:count(3)" },
        {
            content: "Suggest channel member not in R&D group",
            trigger: ".o-mail-Composer-suggestion strong:text(Consultant User)",
        },
        {
            content: "Suggest non-channel member in R&D group",
            trigger: ".o-mail-Composer-suggestion strong:text(Dev User)",
        },
    ],
});
