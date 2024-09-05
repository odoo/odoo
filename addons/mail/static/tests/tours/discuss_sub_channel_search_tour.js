import { contains, scroll } from "@web/../tests/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_discuss_sub_channel_search", {
    test: true,
    steps: () => [
        {
            trigger: "button[title='Show threads']",
            run: "click",
        },
        {
            trigger: ".o-mail-SubChannelList",
            async run() {
                // 30 newest sub channels are loaded initially.
                for (let i = 99; i > 69; i--) {
                    await contains(".o-mail-SubChannelList .o-mail-NotificationItem", {
                        text: `Sub Channel ${i}`,
                    });
                }
            },
        },
        {
            trigger: ".o-mail-SubChannelList .o_searchview_input",
            run: "edit Sub Channel 10",
        },
        {
            trigger: ".o-mail-SubChannelList button[aria-label='Search button']",
            run: "click",
        },
        {
            trigger: ".o-mail-NotificationItem:contains(Sub Channel 10)",
            async run() {
                await contains(".o-mail-SubChannelList .o-mail-NotificationItem", {
                    count: 1,
                });
            },
        },
        {
            trigger: ".o_searchview_input",
            run: "clear",
        },
        {
            trigger: ".o-mail-NotificationItem:contains(Sub Channel 99)",
            async run() {
                // 30 newest sub channels are shown in addition to the one that
                // was fetched during the search.
                for (let i = 99; i > 69; i--) {
                    await contains(".o-mail-SubChannelList .o-mail-NotificationItem", {
                        text: `Sub Channel ${i}`,
                    });
                }
                await contains(".o-mail-SubChannelList .o-mail-NotificationItem", {
                    text: `Sub Channel 10`,
                });
                // Ensure lazy loading is still working after a search.
                await scroll(".o-mail-ActionPanel:has(.o-mail-SubChannelList)", "bottom");
            },
        },
        {
            trigger: ".o-mail-NotificationItem:contains(Sub Channel 40)",
        },
    ],
});
