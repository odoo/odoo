/** @odoo-module */

import { registry } from "@web/core/registry";
import { openPowerbox } from '@knowledge/../tests/tours/knowledge_tour_utils';

const createEmbeddedFileSteps = [
    { // open the powerBox
        trigger: '.odoo-editor-editable p',
        run: function () {
            openPowerbox(this.anchor);
        },
    }, { // click on the /media command
        trigger: '.o-we-command-name:contains("Media")',
        run: 'click',
    }, { // Pick  the "Documents" tab
        trigger: '.o_select_media_dialog .nav-tabs .nav-link:contains("Documents")',
        run: 'click',
    }, { // choose "Onboarding" file
        trigger: '.o_existing_attachment_cell .o_file_name:contains("Onboarding")',
        run: 'click',
    },
];

registry.category("web_tour.tours").add('helpdesk_pick_file_as_attachment_from_knowledge', {
    url: '/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
    steps: () => [{ // click on the first record of the list
    trigger: 'tr.o_data_row:first-child .o_data_cell[name="name"]',
    run: 'click',
}, { // open an article
    trigger: 'button[title="Search Knowledge Articles"]',
    run: 'click',
}, { // click on the first command of the command palette
    trigger: '.o_command_palette_listbox #o_command_0',
    run: 'click',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, ...createEmbeddedFileSteps,
{ // click on the "Use as Attachment" button located in the toolbar of the file block
    trigger: '[data-embedded="file"] .o_embedded_toolbar_button_text:contains("Attach")',
    run: 'click',
}, { // check that the file is added to the attachments
    trigger: '.o-mail-Chatter .o-mail-AttachmentCard:not(.o-isUploading):contains("Onboarding")',
}]});

registry.category("web_tour.tours").add('helpdesk_pick_file_as_message_attachment_from_knowledge', {
    url: '/odoo/action-helpdesk.helpdesk_ticket_action_main_tree',
    steps: () => [{ // click on the first record of the list
    trigger: 'tr.o_data_row:first-child .o_data_cell[name="name"]',
    run: 'click',
}, { // open an article
    trigger: 'button[title="Search Knowledge Articles"]',
    run: 'click',
}, { // click on the first command of the command palette
    trigger: '.o_command_palette_listbox #o_command_0',
    run: 'click',
}, { // wait for Knowledge to open
    trigger: '.o_knowledge_form_view',
}, ...createEmbeddedFileSteps,
{ // click on the "Use as Attachment" button located in the toolbar of the file block
    trigger: '[data-embedded="file"] .o_embedded_toolbar_button_text:contains("Send")',
    run: 'click',
}, { // check that the file is added to the attachment of the message, and that the file finished being uploaded
    trigger: '.o-mail-Chatter .o-mail-Composer .o-mail-AttachmentCard:not(.o-isUploading):contains("Onboarding") i.fa-check',
}]});
