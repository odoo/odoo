odoo.define('crm.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('crm_tour', {
    url: "/web",
}, [tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"], .oe_menu_toggler[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t("Ready to boost your sales? Your <b>Pipeline</b> can be found here, under <b>CRM</b> app."),
    position: 'bottom',
}, {
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_opportunity_kanban',
    content: _t("Click here to <b>create your first opportunity</b> and add it to your pipeline."),
    position: "right"
}, {
    trigger: ".modal-body input:first",
    auto: true,
    run: function (actions) {
        actions.auto();
        actions.auto(".modal-footer .btn-primary");
    },
}, {
    trigger: ".o_opportunity_kanban .o_kanban_group:first-child .o_kanban_record:last-child",
    content: _t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle."),
    position: "right",
    run: "drag_and_drop .o_opportunity_kanban .o_kanban_group:eq(2) ",
}, {
    trigger: ".o_kanban_record:not(.o_updating) .o_activity_color_default",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("This opportunity has <b>no activity planned</b>. <i>Click to check them.</i>"),
    position: "bottom"
}, {
    trigger: ".o_schedule_activity",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Schedule an activity by clicking here"),
    position: "bottom"
}, {
    trigger: ".modal-body .o_field_many2one",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("<p>You will be able to customize your followup activities. Examples:</p><ol><li>introductory email</li><li>call 10 days after</li><li>second call 3 days after, ...</li></ol><p class='mb0'><i>Select a standard activity for now on.</i></p>"),
    position: "bottom",
    run: function (actions) {
        actions.auto(".modal-footer .btn-default");
    },
}, {
    trigger: ".o_kanban_record",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Click on an opportunity to zoom to it."),
    position: "bottom",
    run: function (actions) {
        actions.auto(".o_kanban_record .oe_kanban_action[data-type=edit]");
    },
}, {
    trigger: ".o_opportunity_form .o_chatter_button_new_message",
    content: _t('<p><b>Send messages</b> to your prospect and get replies automatically attached to this opportunity.</p><p class="mb0">Type <i>\'@\'</i> to mention people - it\'s like cc-ing on emails.</p>'),
    position: "bottom"
}, {
    trigger: ".breadcrumb li:not(.active):last",
    extra_trigger: '.o_opportunity_form',
    content: _t("Use the breadcrumbs to <b>go back to your sales pipeline</b>."),
    position: "bottom"
}, tour.STEPS.TOGGLE_APPSWITCHER,
tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="base.menu_administration"], .oe_menu_toggler[data-menu-xmlid="base.menu_administration"]',
    content: _t("Configuration options are available in the Settings app."),
    position: "bottom"
}, {
    trigger: ".o_web_settings_dashboard textarea#user_emails",
    content: _t("<b>Invite coworkers</b> via email.<br/><i>Enter one email per line.</i>"),
    position: "right"
}, tour.STEPS.TOGGLE_APPSWITCHER,
tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"], .oe_menu_toggler[data-menu-xmlid="crm.crm_menu_root"]',
    content: _t("Good job! Your completed the tour of the CRM. You can continue with the <b>implementation guide</b> to help you setup the CRM in your company."),
    position: 'bottom',
}, {
    trigger: '.o_planner_systray div.progress',
    content: _t("Use the <b>implementation guide</b> to setup the CRM in your company."),
    position: 'bottom',
}]);

});
