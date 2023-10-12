/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add('crm_tour', {
    url: "/web",
    rainbowManMessage: _t("Congrats, best of luck catching such big fish! :)"),
    sequence: 10,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: markup(_t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.')),
    position: 'bottom',
    edition: 'community',
}, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: markup(_t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.')),
    position: 'bottom',
    edition: 'enterprise',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_opportunity_kanban',
    content: markup(_t("<b>Create your first opportunity.</b>")),
    position: 'bottom',
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name='partner_id']",
    content: markup(_t('<b>Write a few letters</b> to look for a company, or create a new one.')),
    position: "top",
    run: function (actions) {
        actions.text("Brandon Freeman", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_kanban_quick_create .o_kanban_add",
    content: markup(_t("Now, <b>add your Opportunity</b> to your Pipeline.")),
    position: "bottom",
}, {
    trigger: ".o_opportunity_kanban .o_kanban_group:first-child .o_kanban_record:last-of-type .oe_kanban_content",
    extra_trigger: ".o_opportunity_kanban",
    content: markup(_t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle.")),
    position: "right",
    run: "drag_and_drop_native .o_opportunity_kanban .o_kanban_group:eq(2) ",
}, {
    // Choose the element that is not going to be moved by the previous step.
    trigger: ".o_opportunity_kanban .o_kanban_group:nth-child(2) .o_kanban_record:not(.o_updating) .o-mail-ActivityButton",
    extra_trigger: ".o_opportunity_kanban",
    content: markup(_t("Looks like nothing is planned. :(<br><br><i>Tip: Schedule activities to keep track of everything you have to do!</i>")),
    position: "bottom",
}, {
    trigger: ".o-mail-ActivityListPopover button:contains(Schedule an activity)",
    extra_trigger: ".o_opportunity_kanban",
    content: markup(_t("Let's <b>Schedule an Activity.</b>")),
    position: "bottom",
    width: 200,
}, {
    trigger: '.modal-footer button[name="action_schedule_activities"]',
    content: markup(_t("All set. Let’s <b>Schedule</b> it.")),
    position: "top",  // dot NOT move to bottom, it would cause a resize flicker, see task-2476595
    run: function (actions) {
        actions.auto('.modal-footer button[special=cancel]');
    },
}, {
    id: "drag_opportunity_to_won_step",
    trigger: ".o_opportunity_kanban .o_kanban_record:last-of-type",
    content: markup(_t("Drag your opportunity to <b>Won</b> when you get the deal. Congrats!")),
    position: "bottom",
    run: "drag_and_drop_native .o_opportunity_kanban .o_kanban_group:eq(3) ",
},  {
    trigger: ".o_kanban_record",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Let’s have a look at an Opportunity."),
    position: "right",
    run: function (actions) {
        actions.auto(".o_kanban_record");
    },
}, {
    trigger: ".o_lead_opportunity_form .o_statusbar_status",
    content: _t("You can make your opportunity advance through your pipeline from here."),
    position: "bottom"
}, {
    trigger: ".breadcrumb-item:not(.active):first",
    content: _t("Click on the breadcrumb to go back to your Pipeline. Odoo will save all modifications as you navigate."),
    position: "bottom",
    run: function (actions) {
        actions.auto(".breadcrumb-item:not(.active):last");
    }
}]});
