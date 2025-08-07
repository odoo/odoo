import { contains, dragenterFiles, dropFiles, scroll } from "@web/../tests/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_discuss_sub_channel_search", {
    steps: () => [
        {
            trigger: "button[title='Threads']",
            run: "click",
        },
        {
            trigger: ".o-mail-SubChannelList",
            async run() {
                // 30 newest sub channels are loaded initially.
                for (let i = 99; i > 69; i--) {
                    await contains(".o-mail-SubChannelList-thread", {
                        text: `Sub Channel ${i}`,
                    });
                    await contains(".o-mail-SubChannelList-thread", { count: 30 });
                }
            },
        },
        {
            trigger: ".o-mail-ActionPanel:has(.o-mail-SubChannelList) .o_searchview_input",
            run: "edit Sub Channel 10",
        },
        {
            trigger:
                ".o-mail-ActionPanel:has(.o-mail-SubChannelList) button[aria-label='Search button']",
            run: "click",
        },
        {
            trigger: ".o-mail-SubChannelList-thread:contains(Sub Channel 10)",
            async run() {
                await contains(".o-mail-SubChannelList-thread", { count: 1 });
            },
        },
        {
            trigger: ".o_searchview_input",
            run: "clear",
        },
        {
            trigger: ".o-mail-SubChannelList-thread:contains(Sub Channel 99)",
            async run() {
                await contains(".o-mail-SubChannelList-thread", { count: 31 });
                // Already fetched sub channels are shown in addition to the one
                // that was fetched during the search.
                for (let i = 99; i > 69; i--) {
                    await contains(".o-mail-SubChannelList-thread", {
                        text: `Sub Channel ${i}`,
                    });
                }
                await contains(".o-mail-SubChannelList-thread", { text: `Sub Channel 10` });
                // Ensure lazy loading is still working after a search.
                await scroll(".o-mail-ActionPanel:has(.o-mail-SubChannelList)", "bottom");
            },
        },
        {
            trigger: ".o-mail-SubChannelList-thread:contains(Sub Channel 40)",
            async run() {
                await contains(".o-mail-SubChannelList-thread", { count: 61 });
                for (let i = 99; i > 39; i--) {
                    await contains(".o-mail-SubChannelList-thread", {
                        text: `Sub Channel ${i}`,
                    });
                }
                await scroll(".o-mail-ActionPanel:has(.o-mail-SubChannelList)", "bottom");
            },
        },
        {
            trigger: ".o-mail-SubChannelList-thread:contains(Sub Channel 11)",
            async run() {
                await contains(".o-mail-SubChannelList-thread", { count: 90 });
                for (let i = 99; i > 9; i--) {
                    await contains(".o-mail-SubChannelList-thread", {
                        text: `Sub Channel ${i}`,
                    });
                }
                await scroll(".o-mail-ActionPanel:has(.o-mail-SubChannelList)", "bottom");
            },
        },
        {
            trigger: ".o-mail-SubChannelList-thread:contains(Sub Channel 0)",
            async run() {
                await contains(".o-mail-SubChannelList-thread", { count: 100 });
                for (let i = 99; i > 0; i--) {
                    await contains(".o-mail-SubChannelList-thread", {
                        text: `Sub Channel ${i}`,
                    });
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("create_thread_for_attachment_without_body", {
    steps: () => [
        {
            content: "Open general channel",
            trigger: '.o-mail-DiscussSidebarChannel-itemName:contains("general")',
            run: "click",
        },
        {
            content: "Drop a file",
            trigger: ".o-mail-DiscussContent-main",
            async run() {
                const files = [new File(["hi there"], "file2.txt", { type: "text/plain" })];
                await dragenterFiles(".o-mail-DiscussContent-main", files);
                await dropFiles(".o-Dropzone", files);
            },
        },
        {
            content: "Click on send button",
            trigger: ".o-mail-Composer-mainActions [title='Send']",
            run: "click",
        },
        {
            content: "Hover on attachment",
            trigger:
                '.o-mail-Message:not(:has(.o-mail-Message-pendingProgress)) .o-mail-AttachmentCard:contains("file2.txt")',
            run: "hover",
        },
        {
            content: "Click on expand button",
            trigger: '.o-mail-Message [title="Expand"]',
            run: "click",
        },
        {
            content: "Create a new thread",
            trigger: '.o-dropdown-item:contains("Create Thread")',
            run: "click",
        },
        {
            content: "Check a new thread is created",
            trigger: '.o-mail-Discuss:contains("New Thread")',
        },
    ],
});
