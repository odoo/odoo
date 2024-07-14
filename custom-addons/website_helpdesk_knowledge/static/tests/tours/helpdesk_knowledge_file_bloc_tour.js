/** @odoo-module */

import { registry } from "@web/core/registry";
import { openCommandBar } from '@knowledge/../tests/tours/knowledge_tour_utils';

const createFileBehaviorSteps = [
    { // open the powerBox
        trigger: '.odoo-editor-editable p',
        run: function () {
            openCommandBar(this.$anchor[0]);
        },
    }, { // click on the /article command
        trigger: '.oe-powerbox-commandName:contains("File")',
        run: 'click',
    }, { // choose "Onboarding" file
        trigger: '.o_existing_attachment_cell .o_file_name:contains("Onboarding")',
        run: 'click',
    },
];

registry.category("web_tour.tours").add('helpdesk_pick_file_as_attachment_from_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_action_main_tree',
    test: true,
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
}, ...createFileBehaviorSteps,
{ // click on the "Use as Attachment" button located in the toolbar of the file block
    trigger: '.o_knowledge_behavior_type_file .o_knowledge_toolbar_button_text:contains("Use as Attachment")',
    run: 'click',
}, { // check that the file is added to the attachments
    trigger: '.o-mail-Chatter .o-mail-AttachmentCard:contains("Onboarding")',
    run: () => {},
}]});

registry.category("web_tour.tours").add('helpdesk_pick_file_as_message_attachment_from_knowledge', {
    url: '/web#action=helpdesk.helpdesk_ticket_action_main_tree',
    test: true,
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
}, ...createFileBehaviorSteps,
{ // click on the "Use as Attachment" button located in the toolbar of the file block
    trigger: '.o_knowledge_behavior_type_file .o_knowledge_toolbar_button_text:contains("Send as Message")',
    run: 'click',
}, { // wait for the file to be uploaded
    trigger: '.o-mail-Composer .o-mail-AttachmentCard i.fa-check',
    run: () => {},
}, { // check that the file is added to the attachment of the message, and that the file finished being uploaded
    trigger: '.o-mail-Chatter .o-mail-Composer .o-mail-AttachmentCard:contains("Onboarding"):not(.o-isUploading)',
    run: () => {},
}]});
