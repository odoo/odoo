import { registry } from "@web/core/registry";

/**
 * This tour depends on data created by python test in charge of launching it.
 * It is not intended to work when launched from interface. It is needed to test
 * an action (action manager) which is not possible to test with QUnit.
 * @see mail/tests/test_mail_composer.py
 */
registry.category("web_tour.tours").add("mail/static/tests/tours/mail_composer_test_tour.js", {
    steps: () => [
        {
            content: "Wait for the chatter to be fully loaded",
            trigger: ".o-mail-Chatter .o-mail-Message:count(1)",
        },
        {
            content: "Click on Send Message",
            trigger: "button:contains(Send message)",
            run: "click",
        },
        {
            content: "Write something in composer",
            trigger: ".o-mail-Composer-input",
            run: "edit blahblah @Not && click body",
        },
        {
            content: "Mention a partner",
            trigger: ".o-mail-Composer-suggestion:contains(Not A Demo User)",
            run: "click",
        },
        {
            content: "Add one file in composer",
            trigger: ".o-mail-Composer button[title='Attach Files']",
            async run({ inputFiles }) {
                const files = [new File(["hello, world"], "file1.txt", { type: "text/plain" })];
                await inputFiles(".o-mail-Composer .o_input_file", files);
            },
        },
        {
            trigger: '.o-mail-AttachmentContainer:not(.o-isUploading):contains("file1.txt")',
        },
        {
            content: "Open full composer",
            trigger: "button[title='Open Full Composer']",
            run: "click",
        },
        {
            content: "Check composer keeps open after pushing Escape",
            trigger: ".o_mail_composer_form_view",
            run: "press Escape",
        },
        {
            content: "Check the earlier provided attachment is listed",
            trigger: ".o_field_mail_composer_attachment_list a:contains(file1.txt)",
        },
        {
            content: "Check subject is autofilled",
            trigger: '[name="subject"] input:value(Jane)',
        },
        {
            content: "Check composer content is kept and contains the user's signature",
            trigger: '.o_field_html[name="body"]:contains(blahblah @Not A Demo User)',
        },
        {
            content: `Full composer should contain mention link from small composer ("@Not A Demo User") in body input)`,
            trigger: '.o_field_html[name="body"] a:contains(@Not A Demo User)',
        },
        /** When opening the full composer for the first time, the system
         * should add the user's signature to the end of the message so
         * that the user can edit it. After adding the signature to
         * the editor, the server shouldn't automatically add the
         * signature to the message (see: Python tests). */
        {
            content: "Full composer should contain the user's signature once.",
            trigger: '.o_field_html[name="body"] .o-signature-container:contains(-- Ernest)',
        },
        {
            content: "Drop a file on the full composer",
            trigger: ".o_mail_composer_form_view .o_form_renderer",
            async run({ dragFiles }) {
                const files = [new File(["hi there"], "file2.txt", { type: "text/plain" })];
                const dropFiles = await dragFiles(files);
                await dropFiles(".o-Dropzone");
            },
        },
        {
            content: "Check the attachment is listed",
            trigger: ".o_field_mail_composer_attachment_list a:contains(file2.txt)",
        },
        {
            content: "Click on the mail template selector",
            trigger: ".mail-composer-template-dropdown-btn",
            run: "click",
        },
        {
            content: "Check a template is listed",
            trigger:
                '.mail-composer-template-dropdown.popover .o-dropdown-item:contains("Test template")',
        },
        {
            content: "Verify admin template is NOT listed",
            trigger:
                ".mail-composer-template-dropdown.popover:not(:has(.o-dropdown-item:contains(Test template for admin)))",
        },
        {
            content: "Send message from full composer",
            trigger: ".o_mail_send",
            run: "click",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("blahblah @Not A Demo User")',
            run: "click",
        },
        {
            content: "Click on envelope to see recipients of message",
            trigger:
                '.o-mail-Message:has(.o-mail-Message-body:contains("blahblah @Not A Demo User")) .o-mail-Message-notification',
            run: "click",
        },
        {
            content: "Check message has correct recipients",
            trigger:
                ".o-mail-MessageNotificationPopover:contains('Not A Demo User (NotADemoUser@mail.com) Jane (jane@example.com) Mitchell Admin (test.admin@test.example.com)')",
        },
        {
            content: "Check message contains the first attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentContainer:contains("file1.txt")',
        },
        {
            content: "Check message contains the second attachment",
            trigger: '.o-mail-Message .o-mail-AttachmentContainer:contains("file2.txt")',
        },
        // Test the full composer input text is kept on closing
        {
            content: "Click on Send Message",
            trigger: "button:contains(Send message)",
            run: "click",
        },
        {
            content: "Open full composer",
            trigger: "button[title='Open Full Composer']",
            run: "click",
        },
        {
            /** When opening the full composer, the system should add the
             * user's signature, as this is a new message and the signature
             * has not yet been added to it. */
            content: "Check that the composer contains the signature",
            trigger: '.o_field_html[name="body"] .o-signature-container:contains(-- Ernest)',
        },
        {
            content: "Write something in full composer",
            trigger: ".note-editable",
            run: "editor keep the content",
        },
        {
            content: "Close full composer",
            trigger: ".btn-close",
            run: "click",
        },
        {
            content: "Check full composer text is kept",
            trigger: ".o-mail-Composer-input:value(keep the content)",
        },
        {
            content: "Open full composer",
            trigger: "button[title='Open Full Composer']",
            run: "click",
        },
        {
            content: "Check that the composer doesn't add the user's signature twice",
            trigger: ".note-editable",
        },
        {
            content: "The composer should not contain the user's signature.",
            trigger: '.o_field_html[name="body"]:not(:has(.o-signature-container))',
        },
        {
            content: "Close full composer",
            trigger: ".btn-close",
            run: "click",
        },
        {
            content: "Send message from chatter",
            trigger: ".o-mail-Composer-send:enabled",
            run: "click",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("keep the content")',
        },
        // Test that the server automatically adds the user's signature to the
        // email when the user didn't open the full composer.
        {
            content: "Click on Send Message",
            trigger: "button:contains(Send message)",
            run: "click",
        },
        {
            content: "Write a message",
            trigger: ".o-mail-Composer-input",
            run: "edit hello world",
        },
        {
            content: "Send message from chatter",
            trigger: ".o-mail-Composer-send:enabled",
            run: "click",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("hello world")',
        },
    ],
});
