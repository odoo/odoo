/** @odoo-module **/

import { createFile, inputFiles } from "web.test_utils_file";

import tour from "web_tour.tour";

tour.register(
    "mail/static/tests/tours/discuss_public_tour.js",
    {
        test: true,
    },
    [
        {
            trigger: ".o-mail-discuss-public",
            extraTrigger: ".o-mail-thread",
        },
        {
            content: "Check that we are on channel page",
            trigger: ".o-mail-thread",
            run() {
                if (!window.location.pathname.startsWith("/discuss/channel")) {
                    console.error("Did not automatically redirect to channel page");
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
                    document.body.classList.add("o_mail_channel_public_modules_loaded");
                });
            },
            extraTrigger: ".o_mail_channel_public_modules_loaded",
        },
        {
            content: "Wait for all modules loaded check in previous step",
            trigger: ".o_mail_channel_public_modules_loaded",
        },
        {
            content: "Write something in composer",
            trigger: ".o-mail-composer-textarea",
            run: "text cheese",
        },
        {
            content: "Add one file in composer",
            trigger: ".o-mail-composer button[aria-label='Attach files']",
            async run() {
                const file = await createFile({
                    content: "hello, world",
                    contentType: "text/plain",
                    name: "text.txt",
                });
                inputFiles(document.querySelector(".o-mail-composer-core-main .o_input_file"), [
                    file,
                ]);
            },
        },
        {
            content: "Check the earlier provided attachment is listed",
            trigger: '.o-mail-attachment-card[title="text.txt"]',
            run() {},
        },
        {
            content: "Send message",
            trigger: ".o-mail-composer-send-button",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-message-body:contains("cheese")',
        },
        {
            content: "Check message contains the attachment",
            trigger: '.o-mail-message .o-mail-attachment-card:contains("text.txt")',
        },
    ]
);
