import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss.invite_by_email", {
    steps: () => [
        // Wait for the auto-open of the memberlist. Otherwise, it will
        // conflict with the opening of the invite panel.
        { trigger: ".o-discuss-ChannelMemberList" },
        {
            trigger: "button[title='Add People']",
            run: "click",
        },
        { trigger: ".modal:has(.o-discuss-ChannelInvitation)" },
        {
            trigger: ".o-discuss-ChannelInvitation-search[placeholder='Enter name or email']",
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
        // Wait for the invited member and for the dialog to close, as the member and
        // the invitation emails are stored by then, and the test asserts them after the tour.
        { trigger: ".o-discuss-ChannelMember:has(:text('john (base.group_user)'))" },
        { trigger: "body:not(:has(.modal))" },
    ],
});
