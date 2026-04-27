/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("approvals_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="approvals.approvals_menu_root"]',
            content: "open approvals app",
            run: "click",
        },
        {
            trigger: "button.oe_kanban_action:first",
            content: "create new request",
            run: "click",
        },
        {
            trigger: '.o_field_widget[name="name"] input',
            content: "give name",
            run: "edit Business Trip To Berlin",
        },
        {
            trigger: '.o_field_widget[name="date_start"] input',
            content: "give start date",
            run: "edit 12/13/2018 13:00:00",
        },
        {
            trigger: '.o_field_widget[name="date_end"] input',
            content: "give end date",
            run: "edit 12/20/2018 13:00:00",
        },
        {
            trigger: '.o_field_widget[name="location"] input',
            content: "give location",
            run: "edit Berlin, Schulz Hotel",
        },
        {
            trigger: 'div[name="reason"] .odoo-editor-editable',
            content: "give description",
            run: "editor (We need to go, because reason (and also for beer)))",
        },
        {
            trigger: 'a:contains("Approver(s)"):first',
            content: "open approvers page",
            run: "click",
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            content: "add an approver",
            run: "click",
        },
        {
            content: "select an approver",
            trigger: ".o_selected_row .o_input_dropdown input",
            run: "edit Marc",
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains(Marc)",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
            content: "save the request",
            run: "click",
        },
        {
            trigger: "button[name=action_confirm]:enabled",
            content: "confirm the request",
            run: "click",
        },
        {
            trigger: ".o-mail-Activity button:contains('Approve')",
            content: "approve the request via activity",
            run: "click",
        },
        {
            trigger: 'button[name="action_withdraw"]',
            content: "withdraw approver",
            run: "click",
        },
        {
            trigger: 'button[name="action_refuse"]',
            content: "refuse request",
            run: "click",
        },
        {
            trigger: 'button[aria-checked="true"][data-value="refused"]',
            content: "wait the request status compute",
        },
        {
            trigger: 'button[name="action_cancel"]',
            content: "cancel request",
            run: "click",
        },
        {
            trigger: 'button[name="action_draft"]',
            content: "back the request to draft",
            run: "click",
        },
        {
            trigger: "button[name=action_confirm]:enabled",
            content: "confirm the request again",
            run: "click",
        },
        {
            trigger: 'button[name="action_approve"]',
            content: "approve request",
            run: "click",
        },
        {
            trigger: 'button[name="action_withdraw"]',
            content: "wait the the request to be approved",
        },
    ],
});
