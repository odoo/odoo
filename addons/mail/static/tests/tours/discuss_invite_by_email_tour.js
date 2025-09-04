import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss.invite_by_email", {
    steps: () => [
        {
            trigger: "button[title='Invite People']",
            run: "click",
        },
        {
            trigger: ".o-discuss-ChannelInvitation-search",
            run: "edit john@test.com",
        },
        {
            trigger: ".o-discuss-ChannelInvitation-selectable:contains('john (base.group_user)')",
            async run({ waitFor, click }) {
                await waitFor(".o-discuss-ChannelInvitation-selectable", {
                    only: true,
                    timeout: 5000,
                });
                await click();
            },
        },
        {
            trigger:
                ".o-discuss-ChannelInvitation-selectedList :contains('john (base.group_user)')",
        },
        {
            trigger: ".o-discuss-ChannelInvitation-search",
            run: "edit unknown_email@test.com",
        },
        {
            trigger: ".o-discuss-ChannelInvitation-selectable:contains('unknown_email@test.com')",
            run: "click",
        },
        {
            trigger:
                ".o-discuss-ChannelInvitation-selectedList :contains('unknown_email@test.com')",
        },
        {
            trigger: "button:contains(Invite to Group Chat)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o-mail-ActionPanel))",
        },
    ],
});
