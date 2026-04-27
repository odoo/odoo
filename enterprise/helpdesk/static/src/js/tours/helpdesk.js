/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("helpdesk_tour", {
    url: "/odoo",
    steps: () => [
        {
    trigger: '.o_app[data-menu-xmlid="helpdesk.menu_helpdesk_root"]',
    content: markup(_t('Want to <b>boost your customer satisfaction</b>?<br/><i>Click Helpdesk to start.</i>')),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: ".o_helpdesk_ticket_btn",
        },
        {
    trigger: 'button.oe_kanban_action',
    content: markup(_t('Let\'s view your <b>team\'s tickets</b>.')),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: ".o_helpdesk_ticket_kanban_view",
        },
        {
    trigger: '.o-kanban-button-new',
    content: markup(_t('Let\'s create your first <b>ticket</b>.')),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: ".o_form_editable",
        },
        {
    trigger: '.o_field_widget input.o_input',
    content: markup(_t('Enter the <b>subject</b> of your ticket <br/><i>(e.g. Problem with my installation, Wrong order, etc.).</i>')),
    tooltipPosition: 'right',
            run: "edit SAP is bad, paid by Odoo",
        },
        {
            trigger: ".o_form_editable",
        },
        {
    isActive: ["manual"],
    trigger: ".o_field_widget[name='partner_id']",
    content: markup(_t('Select the <b>customer</b> of your ticket.')),
    tooltipPosition: "top",
    run: "click",
        },
        {
    isActive: ["auto"],
    trigger: 'div[name=partner_id] input',
    content: markup(_t('Select the <b>customer</b> of your ticket.')),
    tooltipPosition: 'top',
            run: "edit Admin",
        },
        {
            trigger: ".o_form_editable",
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:not(:has(i.fa))",
            run: "click",
            tooltipPosition: "right",
        },
        {
            trigger: ".o_form_view",
        },
        {
    trigger: '.o_kanban_quick_create button.o_kanban_add',
    content: _t('Save this ticket and the modifications you\'ve made to it.'),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
    trigger: '.o_kanban_record',
    content: _t('Open the ticket.'),
    tooltipPosition: 'bottom',
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
    trigger: ".o-mail-Chatter-topbar button.o-mail-Chatter-sendMessage",
    content: markup(_t("Use the chatter to <b>send emails</b> and communicate efficiently with your customers. Add new people to the followers' list to make them aware of the progress of this ticket.")),
    tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
    trigger: "button.o-mail-Chatter-logNote",
    content: markup(_t("<b>Log notes</b> for internal communications (you will only notify the persons you specifically tag). Use <b>@ mentions</b> to ping a colleague or <b># mentions</b> to contact a group of people.")),
    tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_saved",
        },
        {
    trigger: "button.o-mail-Chatter-activity",
    content: markup(_t("Use <b>activities</b> to organize your daily work.")),
    run: "click",
        },
        {
    trigger: ".modal-dialog .btn-primary",
    content: markup(_t("Schedule your <b>activity</b>.")),
    tooltipPosition: "right",
    run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
    trigger: '.o_back_button',
    content: markup(_t("Let's go back to the <b>kanban view</b> to get an overview of your next tickets.")),
    tooltipPosition: 'bottom',
    run: "click",
        },
        {
    trigger: 'body:not(:has(div.o_view_sample_data)) .o_helpdesk_ticket_kanban_view .o_kanban_record',
    content: markup(_t('<b>Drag &amp; drop</b> the card to change the stage of your ticket.')),
    tooltipPosition: 'right',
            run: "drag_and_drop(.o_kanban_group:eq(2))",
        },
        {
    trigger: ".o_column_quick_create .o_quick_create_folded",
    content: markup(_t('Adapt your <b>pipeline</b> to your workflow by adding <b>stages</b> <i>(e.g. Awaiting Customer Feedback, etc.).</i>')),
    tooltipPosition: 'bottom',
    run: "click",
        },
        {
    trigger: ".o_column_quick_create .o_kanban_add",
    content: _t("Add your stage and place it at the right step of your workflow by dragging & dropping it."),
    tooltipPosition: 'bottom',
    run: "click",
        },
        {
            trigger: ".o_column_quick_create .o_kanban_add",
            content:
                "Clicking on 'Add' when input name is empty won't do anything, 'Add' will still be displayed",
        },
    ],
});
