import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('crm_tour', {
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: markup(_t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.')),
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: markup(_t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.')),
    run: "click",
},
{
    trigger: ".o_opportunity_kanban .o_kanban_renderer",
},
{
    trigger: '.o_opportunity_kanban .o-kanban-button-new',
    content: markup(_t("<b>Create your first opportunity.</b>")),
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".o_kanban_quick_create .o_field_widget[name='partner_id'] input",
    content: markup(_t('<b>Write a few letters</b> to look for a company, or create a new one.')),
    tooltipPosition: "top",
    run: "edit Brandon Freeman",
}, {
    isActive: ["auto", "desktop"],
    trigger: ".ui-menu-item > a:contains('Brandon Freeman')",
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_kanban_quick_create .o_field_widget[name='partner_id'] input",
    content: _t('Write a few letters to look for a company, or create a new one.'),
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".modal .o_create_button",
    content: _t("Create the contact."),
    run: "click",
}, {
    isActive: ["mobile"],
    trigger: ".o_dialog .o_field_widget[name='name'] input",
    content: _t("Enter the contact's name."),
    run: "edit Brandon Freeman",
}, {
    isActive: ["mobile"],
    trigger: ".o_dialog .o_form_button_save",
    content: _t("Save the contact."),
    run: "click",
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name='name'] input:value('Brandon Freeman')",
}, {
    trigger: ".o_kanban_quick_create .o_kanban_add",
    content: markup(_t("Now, <b>add your Opportunity</b> to your Pipeline.")),
    run: "click",
},
{
    trigger: ".o_opportunity_kanban .o_kanban_renderer",
},
{
    trigger: ".o_opportunity_kanban:not(:has(.o_view_sample_data)) .o_kanban_group .o_kanban_record:last-of-type",
    content: markup(_t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle.")),
    tooltipPosition: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(1))",
},
{
    trigger: ".o_opportunity_kanban .o_kanban_renderer",
},
{
    // Choose the element that is not going to be moved by the previous step.
    trigger: ".o_opportunity_kanban .o_kanban_group .o_kanban_record .o-mail-ActivityButton",
    content: markup(_t("Looks like nothing is planned. :(<br><br><i>Tip: Schedule activities to keep track of everything you have to do!</i>")),
    run: "click",
},
{
    trigger: ".o_opportunity_kanban .o_kanban_renderer",
},
{
    trigger: ".o-mail-ActivityListPopover button:contains(Schedule an activity)",
    content: markup(_t("Let's <b>Schedule an Activity.</b>")),
    run: "click",
}, {
    trigger: '.modal-footer button[name="action_schedule_activities"]',
    content: markup(_t("All set. Let’s <b>Schedule</b> it.")),
    tooltipPosition: "top",  // dot NOT move to bottom, it would cause a resize flicker, see task-2476595
    run: "click",
}, {
    trigger: ".o_kanban_record",
    content: _t("Let’s have a look at an Opportunity."),
    tooltipPosition: "right",
    run: "click",
}, {
    trigger: ".o_lead_opportunity_form .o_statusbar_status",
    content: _t("You can make your opportunity advance through your pipeline by clicking on stages here. Try sending it to the next stage!"),
    run: "click",
}, {
    isActive: ["desktop"],
    trigger: ".breadcrumb-item:not(.active):first",
    content: _t("Click on the breadcrumbs to go back to your Pipeline. Odoo will save all your changes as you navigate."),
    run: "click .breadcrumb-item:not(.active):last",
}, {
    isActive: ["mobile"],
    trigger: ".o_back_button",
    content: _t("Click on the breadcrumbs to go back to your Pipeline. Odoo will save all your changes as you navigate."),
    run: "click",
}, {
    id: "drag_opportunity_to_won_step",
    trigger: ".o_opportunity_kanban .o_kanban_record:last-of-type",
    content: markup(_t("Drag your opportunity to <b>Won</b> when you get the deal. Congrats!")),
    tooltipPosition: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(3))",
},]});
