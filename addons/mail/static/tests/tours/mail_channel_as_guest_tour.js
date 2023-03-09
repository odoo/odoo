/** @odoo-module **/

import { registry } from "@web/core/registry";
import { createFile, inputFiles } from "web.test_utils_file";

registry.category("web_tour.tours").add("mail/static/tests/tours/mail_channel_as_guest_tour.js", {
    test: true,
    steps: [
        {
            content: "Channel secret token has been hidden on welcome page",
            trigger: ".o-mail-welcome-page",
            run() {
                if (!window.location.pathname.startsWith("/discuss/channel")) {
                    console.error("Channel secret token is still present in URL.");
                }
            },
        },
        {
            content: "Click join",
            trigger: "button[title='Join Channel']",
            extraTrigger: ".o-mail-thread",
        },
        {
            content: "Check that we are on channel page",
            trigger: ".o-mail-thread",
            run() {
                // Wait for modules to be loaded or failed for the next step
                odoo.__DEBUG__.didLogInfo.then(() => {
                    const { missing, failed, unloaded } = odoo.__DEBUG__.jsModules;
                    if ([missing, failed, unloaded].some((arr) => arr.length)) {
                        console.error(
                            "Couldn't load all JS modules.",
                            JSON.stringify({ missing, failed, unloaded })
                        );
                    }
                    document.body.classList.add("o_mail_channel_as_guest_tour_modules_loaded");
                });
            },
            extraTrigger: ".o_mail_channel_as_guest_tour_modules_loaded",
        },
        {
            content: "Wait for all modules loaded check in previous step",
            trigger: ".o_mail_channel_as_guest_tour_modules_loaded",
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
            extra_trigger: ".o-mail-attachment-card:not(.o-mail-is-uploading)", // waiting the attachment to be uploaded
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
    ],
});
