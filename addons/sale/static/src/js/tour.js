odoo.define('sale.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('sale_tour', {
    url: "/web",
}, [tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="sales_team.menu_base_partner"], .oe_menu_toggler[data-menu-xmlid="sales_team.menu_base_partner"]',
    content: _t('Organize your sales activities with the <b>Sales app</b>.'),
    position: 'bottom',
}, {
    trigger: ".oe_kanban_action_button",
    extra_trigger: '.o_salesteam_kanban',
    content: _t("Let\'s have a look at the quotations of this sales channel."),
    position: "bottom",
    id: "quotation_button_on_dashboard",
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order",
    content: _t("Let's create a new quotation.<br/><i>Note that colored buttons usually points to the next logical actions in any screen.</i>"),
    position: "right",
}, {
    trigger: ".o_form_required input",
    extra_trigger: ".o_sale_order",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "top",
    run: "text Agrolait",
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_form_field_x2many_list_row_add > a",
    extra_trigger: ".o_sale_order",
    content: _t("Click here to add some lines to your quotations."),
    position: "bottom",
}, {
    trigger: ".modal-body .o_form_required input, .o_list_editable .o_form_required input",
    extra_trigger: ".o_sale_order",
    content: _t("Select a product, or create a new one on the fly. The product will define the default sale price (that you can change), taxes and description automatically."),
    position: "right",
    run: "text Ipad",
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
    run: function (actions) {
        actions.auto();
        actions.auto(".modal-footer .btn-primary");
    },
    id: "quotation_product_selected",
}, {
    trigger: ".o_form_button_save",
    extra_trigger: ".o_sale_order",
    content: _t("Once your quotation is ready, you can save, print or send it by email."),
    position: "right",
}, {
    trigger: ".o_sale_confirm",
    extra_trigger: ".o_sale_order.o_form_readonly",
    content: _t("<p><b>Confirm the order</b> if the customer purchases.</p>"),
    position: "bottom"
}, {
    trigger: ".breadcrumb li:not(.active):last",
    extra_trigger: ".o_sale_order [data-id='sale'].btn-primary, .o_sale_order [data-id='sale'].oe_active",
    content: _t("Use the breadcrumbs to <b>go back to preceeding screens</b>."),
    position: "bottom"
}, {
    trigger: 'li a[data-menu-xmlid="sales_team.menu_sales"], .oe_secondary_menu_section[data-menu-xmlid="sales_team.menu_sales"]',
    content: _t("Use this menu to access quotations, sales orders and customers."),
    edition: "enterprise",
    position: "bottom"
}, tour.STEPS.TOGGLE_APPSWITCHER,
tour.STEPS.MENU_MORE, {
    trigger: '.o_app[data-menu-xmlid="base.menu_administration"], .oe_menu_toggler[data-menu-xmlid="base.menu_administration"]',
    content: _t("Configuration options are available in the Settings app."),
    position: "bottom"
}, {
    trigger: ".o_web_settings_dashboard textarea#user_emails",
    content: _t("<b>Invite salespeople or managers</b> via email.<br/><i>Enter one email per line.</i>"),
    position: "right"
}]);

});
