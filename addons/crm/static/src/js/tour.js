odoo.define('crm.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('crm_tour', {
    'skip_enabled': true,
}, [{
    trigger: '.o_app[data-menu-xmlid="sales_team.menu_base_partner"], .oe_menu_toggler[data-menu-xmlid="sales_team.menu_base_partner"]',
    content: _t("Ready to boost you sales? It starts with the <b>CRM app</b>."),
    position: 'bottom',
}, {
    trigger: ".o_welcome_content .o_dashboard_action",
    extra_trigger: '.o_sales_dashboard',
    content: _t("Let\'s have a look at your opportunities pipeline."),
    position: "bottom"
}, {
    trigger: ".o-kanban-button-new",
    extra_trigger: '.o_opportunity_kanban',
    content: _t("Create your first business opportunity."),
    position: "right"
}, {
    trigger: ".o_opportunity_kanban .o_kanban_record:nth-child(2)",
    content: _t("<b>Drag &amp; drop opportunities</b> between columns as you progress in your sales cycle."),
    position: "right"
}, {
    trigger: ".o_kanban_record .oe_kanban_status_red",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("This opportunity has <b>no next activity scheduled</b>. <i>Click to set one.</i>"),
    position: "bottom"
}, {
    trigger: ".o_recommended_activity .o_radio_item:first()",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("<p>You will be able to customize your followup activities. Examples:</p><ol><li>introductory email</li><li>call 10 days after</li><li>second call 3 days after, ...</li></ol><p class='mb0'><i>Select a standard activity for now on.</i></p>"),
    position: "left"
}, {
    trigger: ".o_kanban_record",
    extra_trigger: ".o_opportunity_kanban",
    content: _t("Click on an opportunity to zoom to it."),
    position: "bottom"
}, {
    trigger: ".o_opportunity_form .o_chatter_button_new_message",
    content: _t('<p><b>Send messages</b> to your prospect and get replies automatically attached to this opportunity.</p><p class="mb0">Type <i>\'@\'</i> to mention people - it\'s like cc-ing on emails.</p>'),
    position: "top"
}, {
    trigger: ".breadcrumb li:not(.active):last",
    extra_trigger: '.o_opportunity_form',
    content: _t("Use the breadcrumbs to <b>go back to your sales pipeline</b>."),
    position: "bottom"
}]);

});
