/* @odoo-module */

import { registry } from "@web/core/registry";
import { createFile, inputFiles } from "@web/../tests/utils";

/**
 * This tour depends on data created by python test in charge of launching it.
 * It is not intended to work when launched from interface. It is needed to test
 * an action (action manager) which is not possible to test with QUnit.
 * @see mail/tests/test_mail_composer.py
 */
registry.category("web_tour.tours").add("mail/static/tests/tours/mail_composer_test_tour.js", {
    test: true,
    steps: () => [
        {
            content: "Click on Send Message",
            trigger: "button:contains(Send message)",
        },
        {
            content: "Write something in composer",
            trigger: ".o-mail-Composer-input",
            run: "text blahblah @",
        },
        {
            content: "Mention a partner",
            trigger: ".o-mail-Composer-suggestion:contains(Marc Demo)",
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
            content: "Open full composer",
            trigger: "button[aria-label='Full composer']",
            extra_trigger: ".o-mail-AttachmentCard:not(.o-isUploading)", // waiting the attachment to be uploaded
        },
        {
            content: "Check composer keeps open after pushing Escape",
            trigger: ".o_mail_composer_form_view",
            run: () => {
                window.dispatchEvent(
                    new KeyboardEvent("keydown", {
                        bubbles: true,
                        key: "Escape",
                    })
                );
            },
        },
        {
            content: "Check the earlier provided attachment is listed",
            trigger: '.o_attachment[title="text.txt"]',
            run() {},
        },
        {
            content: "Check subject is autofilled",
            trigger: '[name="subject"] input',
            run() {
                const subjectValue = document.querySelector('[name="subject"] input').value;
                if (subjectValue !== "Ernest Employee") {
                    console.error(
                        `Full composer should have "Ernest Employee" in subject input (actual: ${subjectValue})`
                    );
                }
            },
        },
        {
            content: "Check composer content is kept",
            trigger: '.o_field_html[name="body"]',
            run() {
                const bodyContent = document.querySelector(
                    '.o_field_html[name="body"]'
                ).textContent;
                if (!bodyContent.includes("blahblah @Marc Demo")) {
                    console.error(
                        `Full composer should contain text from small composer ("blahblah @Marc Demo") in body input (actual: ${bodyContent})`
                    );
                }
                const mentionLink = document.querySelector(
                    '.o_field_html[name="body"] a'
                ).textContent;
                if (!mentionLink.includes("@Marc Demo")) {
                    console.error(
                        `Full composer should contain mention link from small composer ("@Marc Demo") in body input)`
                    );
                }
            },
        },
        {
            content: "Open templates",
            trigger: '.o_field_widget[name="template_id"] input',
        },
        {
            content: "Check a template is listed",
            in_modal: false,
            trigger: '.ui-autocomplete .ui-menu-item a:contains("Test template")',
            run() {},
        },
        {
            content: "Send message",
            trigger: ".o_mail_send",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("blahblah @Marc Demo")',
        },
        {
            content: "Check message contains the attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentCard:contains("text.txt")',
            isCheck: true,
        },
    ],
});
