/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('crm_tour', {
    url: "/odoo",
    steps: () => [stepUtils.showAppsMenuItem(), {
    isActive: ["community"],
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: markup(_t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.')),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    isActive: ["enterprise"],
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: markup(_t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.')),
    tooltipPosition: 'bottom',
    run: "click",
},
{
    isActive: ["auto"],
    trigger: ".o_opportunity_kanban",
},
{
    trigger: '.o_opportunity_kanban .o-kanban-button-new',
    content: markup(_t("<b>Create your first opportunity.</b>")),
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name='partner_id'] input",
    content: markup(_t('<b>Write a few letters</b> to look for a company, or create a new one.')),
    tooltipPosition: "top",
    run: "edit Brandon Freeman",
}, {
    isActive: ["auto"],
    trigger: ".ui-menu-item > a",
    run: "click",
}, {
    trigger: ".o_kanban_quick_create .o_kanban_add",
    content: markup(_t("Now, <b>add your Opportunity</b> to your Pipeline.")),
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["auto"],
    trigger: ".o_opportunity_kanban",
},
{
    trigger: ".o_opportunity_kanban .o_kanban_group:first-child .o_kanban_record:last-of-type",
    content: markup(_t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle.")),
    tooltipPosition: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(2))",
},
{
    isActive: ["auto"],
    trigger: ".o_opportunity_kanban",
},
{
    // Choose the element that is not going to be moved by the previous step.
    trigger: ".o_opportunity_kanban .o_kanban_group .o_kanban_record .o-mail-ActivityButton",
    content: markup(_t("Looks like nothing is planned. :(<br><br><i>Tip: Schedule activities to keep track of everything you have to do!</i>")),
    tooltipPosition: "bottom",
    run: "click",
},
{
    isActive: ["auto"],
    trigger: ".o_opportunity_kanban",
},
{
    trigger: ".o-mail-ActivityListPopover button:contains(Schedule an activity)",
    content: markup(_t("Let's <b>Schedule an Activity.</b>")),
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: '.modal-footer button[name="action_schedule_activities"]',
    content: markup(_t("All set. Let’s <b>Schedule</b> it.")),
    tooltipPosition: "top",  // dot NOT move to bottom, it would cause a resize flicker, see task-2476595
    run: "click",
}, {
    id: "drag_opportunity_to_won_step",
    trigger: ".o_opportunity_kanban .o_kanban_record:last-of-type",
    content: markup(_t("Drag your opportunity to <b>Won</b> when you get the deal. Congrats!")),
    tooltipPosition: "right",
    run: "drag_and_drop(.o_opportunity_kanban .o_kanban_group:eq(3))",
},
{
    isActive: ["auto"],
    trigger: ".o_opportunity_kanban",
},
{
    trigger: ".o_kanban_record",
    content: _t("Let’s have a look at an Opportunity."),
    tooltipPosition: "right",
    run: "click",
}, {
    trigger: ".o_lead_opportunity_form .o_statusbar_status",
    content: _t("You can make your opportunity advance through your pipeline from here."),
    tooltipPosition: "bottom",
    run: "click",
}, {
    trigger: ".breadcrumb-item:not(.active):first",
    content: _t("Click on the breadcrumb to go back to your Pipeline. Odoo will save all modifications as you navigate."),
    tooltipPosition: "bottom",
    run: "click .breadcrumb-item:not(.active):last",
}]});
