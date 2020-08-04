odoo.define('mail/static/tests/tours/mail_full_composer_test_tour.js', function (require) {
"use strict";

const {
    createFile,
    inputFiles,
} = require('web.test_utils_file');

const tour = require('web_tour.tour');

/**
 * This tour depends on data created by python test in charge of launching it.
 * It is not intended to work when launched from interface. It is needed to test
 * an action (action manager) which is not possible to test with QUnit.
 * @see mail/tests/test_mail_full_composer.py
 */
tour.register('mail/static/tests/tours/mail_full_composer_test_tour.js', {
    test: true,
}, [{
    content: "Click on Send Message",
    trigger: '.o_ChatterTopbar_buttonSendMessage',
}, {
    content: "Write something in composer",
    trigger: '.o_ComposerTextInput_textarea',
    run: 'text blahblah',
}, {
    content: "Add one file in composer",
    trigger: '.o_Composer_buttonAttachment',
    async run() {
        const file = await createFile({
            content: 'hello, world',
            contentType: 'text/plain',
            name: 'text.txt',
        });
        inputFiles(
            document.querySelector('.o_FileUploader_input'),
            [file]
        );
    },
}, {
    content: "Open full composer",
    trigger: '.o_Composer_buttonFullComposer',
    extra_trigger: '.o_Attachment:not(.o-temporary)' // waiting the attachment to be uploaded
}, {
    content: "Check the earlier provided attachment is listed",
    trigger: '.o_attachment[title="text.txt"]',
    run() {},
}, {
    content: "Check subject is autofilled",
    trigger: 'input[name="subject"]',
    run() {
        const subjectValue = document.querySelector('input[name="subject"]').value;
        if (subjectValue !== "Re: Test User") {
            console.error(
                `Full composer should have "Re: Test User" in subject input (actual: ${subjectValue})`
            );
        }
    },
}, {
    content: "Check composer content is kept",
    trigger: '.oe_form_field[name="body"]',
    run() {
        const bodyContent = document.querySelector('.oe_form_field[name="body"] textarea').textContent;
        if (!bodyContent.includes("blahblah")) {
            console.error(
                `Full composer should contain text from small composer ("blahblah") in body input (actual: ${bodyContent})`
            );
        }
    },
}, {
    content: "Open templates",
    trigger: '.o_field_widget[name="template_id"] input',
}, {
    content: "Check a template is listed",
    in_modal: false,
    trigger: '.ui-autocomplete .ui-menu-item a:contains("Test template")',
    run() {},
}, {
    content: "Send message",
    trigger: '.o_mail_send',
}, {
    content: "Check message is shown",
    trigger: '.o_Message:contains("blahblah")',
}, {
    content: "Check message contains the attachment",
    trigger: '.o_Message .o_Attachment_filename:contains("text.txt")',
}]);

});
