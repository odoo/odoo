/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('helpdesk_tour', {
    url: "/web",
    rainbowManMessage: () => markup(_t('<center><strong><b>Good job!</b> You walked through all steps of this tour.</strong></center>')),
    sequence: 220,
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="helpdesk.menu_helpdesk_root"]',
    content: markup(_t('Want to <b>boost your customer satisfaction</b>?<br/><i>Click Helpdesk to start.</i>')),
    position: 'bottom',
}, {
    trigger: '.oe_kanban_action_button',
    extra_trigger: '.o_kanban_primary_left',
    content: markup(_t('Let\'s view your <b>team\'s tickets</b>.')),
    position: 'bottom',
    width: 200,
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_helpdesk_ticket_kanban_view',
    content: markup(_t('Let\'s create your first <b>ticket</b>.')),
    position: 'bottom',
    width: 200,
}, {
    trigger: '.field_name textarea',
    extra_trigger: '.o_form_editable',
    content: markup(_t('Enter the <b>subject</b> of your ticket <br/><i>(e.g. Problem with my installation, Wrong order, etc.).</i>')),
    position: 'right',
}, {
    trigger: '.o_field_widget.field_partner_id',
    extra_trigger: '.o_form_editable',
    content: markup(_t('Select the <b>customer</b> of your ticket.')),
    position: 'top',
}, {
    trigger: '.o_field_widget.field_user_id',
    extra_trigger: '.o_form_editable',
    content: markup(_t('Assign the ticket to a <b>member of your team</b>.')),
    position: 'right',
}, {
    trigger: ".o-mail-Chatter-topbar button:contains(Send message)",
    extra_trigger: '.o_form_view',
    content: markup(_t("Use the chatter to <b>send emails</b> and communicate efficiently with your customers. Add new people to the followers' list to make them aware of the progress of this ticket.")),
    width: 350,
    position: "bottom",
}, {
    trigger: "button:contains(Log note)",
    extra_trigger: '.o_form_view',
    content: markup(_t("<b>Log notes</b> for internal communications (you will only notify the persons you specifically tag). Use <b>@ mentions</b> to ping a colleague or <b># mentions</b> to contact a group of people.")),
    width: 350,
    position: "bottom"
}, {
    trigger: "button:contains(Activities)",
    extra_trigger: '.o_form_view .o_form_saved',
    content: markup(_t("Use <b>activities</b> to organize your daily work.")),
}, {
    trigger: ".modal-dialog .btn-primary",
    content: markup(_t("Schedule your <b>activity</b>.")),
    position: "right",
    run: "click",
}, {
    trigger: '.o_back_button',
    extra_trigger: '.o_form_view',
    content: markup(_t("Let's go back to the <b>kanban view</b> to get an overview of your next tickets.")),
    position: 'bottom',
}, {
    trigger: 'body:not(:has(div.o_view_sample_data)) .o_helpdesk_ticket_kanban_view .o_kanban_record',
    content: markup(_t('<b>Drag &amp; drop</b> the card to change the stage of your ticket.')),
    position: 'right',
    run: "drag_and_drop .o_kanban_group:eq(2) ",
}, {
    trigger: ".o_column_quick_create .o_quick_create_folded",
    content: markup(_t('Adapt your <b>pipeline</b> to your workflow by adding <b>stages</b> <i>(e.g. Awaiting Customer Feedback, etc.).</i>')),
    position: 'right',
}, {
    trigger: ".o_column_quick_create .o_kanban_add",
    content: _t("Add your stage and place it at the right step of your workflow by dragging & dropping it."),
    position: 'right',
}, {
    trigger: ".o_column_quick_create .o_kanban_add",
    content: "Clicking on 'Add' when input name is empty won't do anything, 'Add' will still be displayed",
    auto: true,
    isCheck: true,
}
]});
