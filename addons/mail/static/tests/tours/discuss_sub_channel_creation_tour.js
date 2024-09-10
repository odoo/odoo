import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_discuss_sub_channel_creation", {
    test: true,
    steps: () => [
        {
            trigger: "button[title='Show threads']",
            run: "click",
        },
        {
            trigger: ":contains(This channel does not have any thread yet.)",
        },
        {
            trigger: ".o-mail-ActionPanel:has(.o-mail-SubChannelList) .o_searchview_input",
            run: "edit MyEpicChannel",
        },
        {
            trigger:
                ".o-mail-ActionPanel:has(.o-mail-SubChannelList) button[aria-label='Search button']",
            run: "click",
        },
        {
            trigger: "button:contains('Create thread')",
            run: "click",
        },
        {
            trigger: ".o-mail-Discuss-threadName[title='MyEpicChannel']",
        },
        {
            trigger:
                ".o-mail-DiscussSidebarChannel:contains(General) ~ ul:has(.o-mail-DiscussSidebar-item:contains(MyEpicChannel))",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(General)",
            run: "click",
        },
        {
            trigger:
                ".o-mail-Message:contains(Thanks! Could you please remind me where is Christine's office, if I may ask? I'm new here!) [title='Expand']",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Create thread')",
            run: "click",
        },
        {
            trigger: ".o-mail-Discuss-threadName[title='Thanks! Could you please remin']",
        },
        {
            trigger:
                ".o-mail-DiscussSidebarChannel:contains(General) ~ ul:has(.o-mail-DiscussSidebar-item:contains(Thanks! Could you please remin))",
        },
        {
            trigger:
                ".o-mail-Message:contains(Thanks! Could you please remind me where is Christine's office, if I may ask? I'm new here!)",
        },
    ],
});
