/** @odoo-module */

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";


registry.category("web_tour.tours").add('helpdesk_pick_template_as_message_from_knowledge', {
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
}, { // click on the "Send as Message" button from the template block
    trigger: '[data-embedded="clipboard"] .o_embedded_toolbar_button_text:contains("Send as Message")',
    run: 'click',
}, { // check that the content of the template block has been added to the mail composer
    trigger: '.o_mail_composer_form .o_field_html p:contains("Hello world")',
}, { // check that the mail composer contains the user's signature
    trigger: '.o_mail_composer_form .o_field_html .o-signature-container:contains("Mitchell Admin")',
}, { // cancel the message, no need to send it and trigger a backend `write` (see discuss tests for that)
    trigger: 'footer button:contains(Discard)',
    run: 'click'
}
]});

registry.category("web_tour.tours").add('helpdesk_pick_template_as_description_from_knowledge', {
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
}, { // click on the "Use as Description" button from the template block
    trigger: '[data-embedded="clipboard"] .o_embedded_toolbar_button_text:contains("Use as Description")',
    run: 'click',
}, { // check that the description contains content of the template block
    trigger: '.o_form_sheet .o_field_html .odoo-editor-editable p:contains("Hello world")',
}, ...stepUtils.discardForm(),
]});
