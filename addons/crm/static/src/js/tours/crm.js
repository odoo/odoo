odoo.define('crm.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('crm_tour', {
    url: "/web",
    rainbowManMessage: _t("Congrats, best of luck catching such big fish! :)"),
    sequence: 5,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.'),
    position: 'bottom',
    edition: 'community',
}, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t('Ready to boost your sales? Let\'s have a look at your <b>Pipeline</b>.'),
    position: 'bottom',
    edition: 'enterprise',
}, {
    trigger: '.o-kanban-button-new',
    extra_trigger: '.o_opportunity_kanban',
    content: _t("<b>Create your first opportunity.</b>"),
    position: 'bottom',
}, {
    trigger: ".o_kanban_quick_create .o_field_widget[name='partner_id']",
    content: _t('<b>Write a few letters</b> to look for a company, or create a new one.'),
    position: "bottom",
    run: function (actions) {
        actions.text("Brandon Freeman", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
}, {
    trigger: '.o_kanban_quick_create .o_field_monetary[name="expected_revenue"] input',
    content: _t("Define here the Expected Revenue of this Opportunity."),
    position: 'right',
    run: "text 12.3",
}, {
    trigger: ".o_kanban_quick_create .o_kanban_add",
    content: _t("Now, <b>add your Opportunity</b> to your Pipeline."),
    position: "bottom",
}, {
    trigger: ".o_opportunity_kanban .o_kanban_group:first-child .o_kanban_record:last-child .oe_kanban_content",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle."),
    position: "bottom",
    run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(2) ",
}, {
    trigger: ".o_kanban_record:not(.o_updating) .o_activity_color_default",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Looks like nothing is planned. :(<br><br><i>Tip : Schedule activities to keep track of everything you have to do!</i>"),
    position: "bottom",
}, {
    trigger: ".o_schedule_activity",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Let's <b>Schedule an Activity.</b>"),
    position: "bottom",
    width: 200,
}, {
    trigger: '.modal-footer button[name="action_close_dialog"]',
    content: _t("All set. Let’s <b>Schedule</b> it."),
    position: "bottom",
    run: function (actions) {
        actions.auto('.modal-footer button[special=cancel]');
    },
}, {
    id: "drag_opportunity_to_won_step",
    trigger: ".o_opportunity_kanban .o_kanban_record:last-child",
    content: _t("Drag your opportunity to <b>Won</b> when you get the deal. Congrats !"),
    position: "bottom",
    run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(3) ",
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
    content: _t("This bar also allows you to switch stage."),
    position: "bottom"
}, {
    trigger: ".breadcrumb-item:not(.active):first",
    content: _t("Click on the breadcrumb to go back to the Pipeline."),
    position: "bottom",
    run: function (actions) {
        actions.auto(".breadcrumb-item:not(.active):last");
    }
}]);

});
