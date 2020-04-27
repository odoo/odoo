odoo.define('crm.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('crm_tour', {
    url: "/web",
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t("Ready to boost your sales? Let’s have a look at your <b>Pipeline</b>."),
    position: 'bottom',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_opportunity_kanban',
    content: _t("<b>Create your first opportunity</b>"),
    position: 'bottom',
}, {
    trigger: ".o_kanban_quick_create input:first",
    content: _t('Look for a Contact or create a new one. Tip : Did you know you can search by VAT Number as well?'),
    position: "right",
}, {
    trigger: ".o_kanban_quick_create input[name='name']",
    content: _t("<b>Choose a name</b> for your opportunity, example: <i>'Need a new website'</i>"),
    position: "right",
}, {
    trigger: '.o_kanban_quick_create .o_field_monetary[name="planned_revenue"]',
    content: _t("Define here the Expected Revenue of this Opportunity."),
    position: 'right',
}, {
    trigger: '.o_kanban_quick_create .o_kanban_add',
    content: _t("Now, <b>add your Opportunity</b> to your Pipeline."),
    position: 'bottom',
}, {
    trigger: ".o_opportunity_kanban .o_kanban_group:first-child .o_kanban_record:last-child",
    content: _t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle."),
    position: "bottom",
    run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(2) ",
}, {
    trigger: ".o_kanban_record:not(.o_updating) .o_activity_color_default",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Looks like nothing is planned. :(Tip : Schedule activities to keep track of everything you have to do!"),
    position: "bottom",
}, {
    trigger: ".o_schedule_activity",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Let's schedule an activity."),
    position: "bottom",
}, {
    trigger: '.modal-body .o_field_char[name="summary"]',
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Let’s do a follow-up next week."),
    position: "bottom",
}, {
    trigger: '.modal-body .o_field_date',
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Choose a deadline."),
    position: "right",
}, {
    trigger: '.modal-footer button[name="action_close_dialog"]',
    content: _t("All set. Let’s Schedule it."),
    position: "bottom",
    run: function (actions) {
        actions.auto('.modal-footer button[special=cancel]');
    },
}, {
    trigger: ".o_opportunity_kanban .o_kanban_group:eq(2) .o_kanban_record:last-child",
    content: _t("Drag your opportunity to Won when you get the deal. Congrats !"),
    position: "bottom",
    run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(3) ",
}, {
    trigger: ".o_button_generate_leads",
    content: _t("Looking for more opportunities ? Try the Lead Generation tool."),
    position: "bottom",
    run: function (actions) {
        actions.auto('.o_button_generate_leads');
    },
}, {
    trigger: '.modal-body .o_industry',
    content: _t("Which Industry do you want to target?"),
    position: "bottom",
}, {
    trigger: '.modal-footer button[name=action_submit]',
    content: _t("Now, just let the magic happen!"),
    position: "bottom",
    run: function (actions) {
        actions.auto('.modal-footer button[special=cancel]');
    },
}, {
    trigger: ".o_kanban_record",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Let’s have a look at an Opportunity."),
    position: "right",
    run: function (actions) {
        actions.auto(".o_kanban_record");
    }
}, {
    trigger: ".o_statusbar_status",
    content: _t("This bar also allows you to switch stage."),
    position: "bottom"
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: '.o_lead_opportunity_form',
    content: _t("Use the breadcrumbs to <b>go back to your sales pipeline</b>."),
    position: "bottom",
    run: function (actions) {
        actions.auto(".breadcrumb-item:not(.active):last");
    }
}]);

});
