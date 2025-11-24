import { SubChannelList } from "@mail/discuss/core/public_web/sub_channel_list";

import { status } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { effect } from "@web/core/utils/reactive";

let waitForLoadMoreToDisappearDef;
registry.category("web_tour.tours").add("test_discuss_sub_channel_search", {
    steps: () => [
        {
            trigger: "body",
            run() {
                patch(SubChannelList.prototype, {
                    setup() {
                        super.setup(...arguments);
                        effect(
                            (state) => {
                                if (status(this) === "destroyed") {
                                    return;
                                }
                                if (!state.isVisible) {
                                    waitForLoadMoreToDisappearDef?.resolve();
                                }
                            },
                            [this.loadMoreState]
                        );
                    },
                });
            },
        },
        {
            trigger: "button[title='Threads']",
            run: "click",
        },
        {
            trigger: ".o-mail-SubChannelList .o-mail-SubChannelPreview:count(30)",
        },
        ...Array.from({ length: 30 }, (_, index) => 99 - index).map((i) => ({
            trigger: `.o-mail-SubChannelPreview:text(Sub Channel ${i})`,
        })),
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
            trigger:
                ".o-mail-SubChannelList .o-mail-SubChannelPreview:count(1):contains(Sub Channel 10)",
            async run() {
                waitForLoadMoreToDisappearDef = new Deferred();
            },
        },
        {
            trigger: ".o_searchview_input",
            run: "clear",
        },
        {
            trigger:
                ".o-mail-SubChannelList .o-mail-SubChannelPreview:count(31):contains(Sub Channel 99)",
        },
        // Already fetched sub channels are shown in addition to the one
        // that was fetched during the search.
        ...Array.from({ length: 30 }, (_, index) => 99 - index).map((i) => ({
            trigger: `.o-mail-SubChannelPreview:text(Sub Channel ${i})`,
        })),
        {
            trigger: ".o-mail-SubChannelPreview:text(Sub Channel 10)",
            async run() {
                // Ensure lazy loading is still working after a search.
                await waitForLoadMoreToDisappearDef;
                waitForLoadMoreToDisappearDef = new Deferred();
            },
        },
        {
            trigger: ".o-mail-ActionPanel:has(.o-mail-SubChannelList)",
            run: "scroll bottom",
        },
        {
            trigger:
                ".o-mail-SubChannelList .o-mail-SubChannelPreview:count(61):contains(Sub Channel 40)",
        },
        ...Array.from({ length: 60 }, (_, index) => 99 - index).map((i) => ({
            trigger: `.o-mail-SubChannelPreview:text(Sub Channel ${i})`,
        })),
        {
            trigger: "body",
            async run() {
                await waitForLoadMoreToDisappearDef;
                waitForLoadMoreToDisappearDef = new Deferred();
            },
        },
        {
            trigger: ".o-mail-ActionPanel:has(.o-mail-SubChannelList)",
            run: "scroll bottom",
        },
        {
            trigger:
                ".o-mail-SubChannelList .o-mail-SubChannelPreview:count(90):contains(Sub Channel 11)",
        },
        ...Array.from({ length: 90 }, (_, index) => 99 - index).map((i) => ({
            trigger: `.o-mail-SubChannelPreview:text(Sub Channel ${i})`,
        })),
        {
            trigger: "body",
            async run() {
                await waitForLoadMoreToDisappearDef;
            },
        },
        {
            trigger: ".o-mail-ActionPanel:has(.o-mail-SubChannelList)",
            run: "scroll bottom",
        },
        {
            trigger:
                ".o-mail-SubChannelList .o-mail-SubChannelPreview:count(100):contains(Sub Channel 0)",
        },
        ...Array.from({ length: 99 }, (_, index) => 99 - index).map((i) => ({
            trigger: `.o-mail-SubChannelPreview:text(Sub Channel ${i})`,
        })),
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
            async run({ dragFiles }) {
                const files = [new File(["hi there"], "file2.txt", { type: "text/plain" })];
                const dropFiles = await dragFiles(files);
                await dropFiles(".o-Dropzone");
            },
        },
        {
            trigger: '.o-mail-AttachmentContainer:not(.o-isUploading):contains("file2.txt")',
        },
        {
            content: "Click on send button",
            trigger: ".o-mail-Composer-mainActions [title='Send']:enabled",
            run: "click",
        },
        {
            content: "Hover on attachment",
            trigger:
                '.o-mail-Message:not(:has(.o-mail-Message-pendingProgress)) .o-mail-AttachmentContainer:contains("file2.txt")',
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
