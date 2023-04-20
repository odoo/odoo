/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createFile, inputFiles } from "web.test_utils_file";

registry.category("web_tour.tours").add("mail/static/tests/tours/discuss_public_tour.js", {
    test: true,
    steps: [
        {
            trigger: ".o-mail-DiscussPublic",
            extraTrigger: ".o-mail-Thread",
        },
        {
            content: "Check that we are on channel page",
            trigger: ".o-mail-Thread",
            run() {
                if (!window.location.pathname.startsWith("/discuss/channel")) {
                    console.error("Channel secret token is still present in URL.");
                }
                // Wait for modules to be loaded or failed for the next step
                odoo.__DEBUG__.didLogInfo.then(() => {
                    const { missing, failed, unloaded } = odoo.__DEBUG__.jsModules;
                    if ([missing, failed, unloaded].some((arr) => arr.length)) {
                        console.error(
                            "Couldn't load all JS modules.",
                            JSON.stringify({ missing, failed, unloaded })
                        );
                    }
                    document.body.classList.add("o_discuss_channel_public_modules_loaded");
                });
            },
            extraTrigger: ".o_discuss_channel_public_modules_loaded",
        },
        {
            content: "Wait for all modules loaded check in previous step",
            trigger: ".o_discuss_channel_public_modules_loaded",
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
                const file = await createFile({
                    content: "hello, world",
                    contentType: "text/plain",
                    name: "text.txt",
                });
                inputFiles(document.querySelector(".o-mail-Composer-coreMain .o_input_file"), [
                    file,
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
            trigger: ".o-mail-Composer-send",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("cheese")',
        },
        {
            content: "Check message contains the attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
        },
    ],
});
