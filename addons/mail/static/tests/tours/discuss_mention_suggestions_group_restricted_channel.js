import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_mention_suggestions_group_restricted_channel.js", {
    steps: () => [
        { trigger: ".o-mail-DiscussContent-threadName[title='R&D Channel']" },
        { trigger: ".o-mail-Composer-html", run: "editor @Consultant User" },
        {
            content: "Suggest channel member not in R&D group",
            trigger: ".o-mail-Composer-suggestion strong:text(Consultant User)",
        },
        { trigger: ".o-mail-Composer-html", run: "editor @Dev User" },
        {
            content: "Suggest non-channel member in R&D group",
            trigger: ".o-mail-Composer-suggestion strong:text(Dev User)",
        },
        { trigger: ".o-mail-Composer-html", run: "editor @Sales User" },
        {
            content: "Do not suggest Sales User, neither a member nor in R&D group",
            trigger: "body:not(:has(.o-mail-Composer-suggestion))",
        },
        { trigger: ".o-mail-NotificationItem:has(:text('Sales Channel'))", run: "click" },
        { trigger: ".o-mail-DiscussContent-threadName[title='Sales Channel']" },
        { trigger: ".o-mail-Composer-html", run: "editor @Sales User" },
        {
            content: "Suggest Sales User where no group restricts the channel",
            trigger: ".o-mail-Composer-suggestion strong:text(Sales User)",
        },
    ],
});
