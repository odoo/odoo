/* @odoo-module */

import { registry } from "@web/core/registry";
import { click, contains, createFile, inputFiles } from "@web/../tests/utils";

registry.category("web_tour.tours").add("discuss_channel_public_tour.js", {
    test: true,
    steps: () => [
        {
            trigger: ".o-mail-DiscussPublic",
            extraTrigger: ".o-mail-Thread",
            run() {},
        },
        {
            content: "Check that we are on channel page",
            trigger: ".o-mail-Thread",
            run() {
                if (!window.location.pathname.startsWith("/discuss/channel")) {
                    console.error("Channel secret token is still present in URL.");
                }
                const { missing, failed, unloaded } = odoo.loader.findErrors();
                if ([missing, failed, unloaded].some((arr) => arr.length)) {
                    console.error(
                        "Couldn't load all JS modules.",
                        JSON.stringify({ missing, failed, unloaded })
                    );
                }
                document.body.classList.add("o_discuss_channel_public_modules_loaded");
            },
            extraTrigger: ".o_discuss_channel_public_modules_loaded",
        },
        {
            content: "Wait for all modules loaded check in previous step",
            trigger: ".o_discuss_channel_public_modules_loaded",
            run() {},
        },
        {
            content: "Write something in composer",
            trigger: ".o-mail-Composer-input",
            run: "text cheese",
        },
        {
            content: "Add one file in composer",
            trigger: ".o-mail-Composer button[aria-label='Attach files']",
            async run() {
                await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
                    await createFile({
                        content: "hello, world",
                        contentType: "text/plain",
                        name: "text.txt",
                    }),
                ]);
            },
        },
        {
            content: "Check the earlier provided attachment is listed",
            trigger: '.o-mail-AttachmentCard[title="text.txt"]',
            extra_trigger: ".o-mail-AttachmentCard:not(.o-isUploading)", // waiting the attachment to be uploaded
            run() {},
        },
        {
            content: "Send message",
            trigger: ".o-mail-Composer-send:enabled",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("cheese")',
            run() {},
        },
        {
            content: "Check message contains the attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
            run() {},
        },
        {
            content: "Click on more menu",
            trigger: ".o-mail-Message [title='Expand']",
        },
        {
            content: "Click on edit",
            trigger: ".o-mail-Message [title='Edit']",
        },
        {
            content: "Edit message",
            trigger: ".o-mail-Message .o-mail-Composer-input",
            run: "text vegetables",
        },
        {
            content: "Add one more file in composer",
            trigger: ".o-mail-Message .o-mail-Composer button[aria-label='Attach files']",
            async run() {
                inputFiles(".o-mail-Message .o-mail-Composer-coreMain .o_input_file", [
                    await createFile({
                        content: "hello 2",
                        contentType: "text/plain",
                        name: "extra.txt",
                    }),
                ]);
            },
        },
        {
            content: "Check the earlier provided extra attachment is listed",
            trigger: '.o-mail-Message .o-mail-Composer .o-mail-AttachmentCard[title="extra.txt"]',
            extra_trigger:
                ".o-mail-Message .o-mail-Composer .o-mail-AttachmentCard:not(.o-isUploading)", // waiting the attachment to be uploaded
            run() {},
        },
        {
            content: "Save edited message",
            trigger: ".o-mail-Message a:contains(save)",
        },
        {
            content: "Check message is edited",
            trigger: '.o-mail-Message-body:contains("vegetables")',
            run() {},
        },
        {
            content: "Check edited message contains the first attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
            run() {},
        },
        {
            content: "Check edited message contains the extra attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("extra.txt")',
            async run() {
                await click(".o-mail-AttachmentCard-unlink", {
                    parent: [".o-mail-AttachmentCard", { text: "extra.txt" }],
                });
                await click(".btn", { text: "Ok", parent: [".modal", { text: "Confirmation" }] });
                await contains(".o-mail-AttachmentCard", { text: "extra.txt", count: 0 });
            },
        },
        {
            content: "Open search panel",
            trigger: "button[title='Search Messages']",
        },
        {
            content: "Search for the attachment name",
            trigger: ".o_searchview_input",
            run: "text text.txt",
        },
        {
            content: "Trigger the search",
            trigger: "button[aria-label='Search button']",
        },
        {
            content: "Check that searched message contains the attachment",
            trigger:
                '.o-mail-SearchMessagesPanel .o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
            run() {},
        },
    ],
});
