odoo.define('sale.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('sale_tour', {
    url: "/web",
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales Management app</b>.'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Organize your sales activities with the <b>Sales Management app</b>.'),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order",
    content: _t("Let's create a new quotation.<br/><i>Note that colored buttons usually point to the next logical actions.</i>"),
    position: "bottom",
}, {
    trigger: ".o_form_editable .o_field_many2one[name='partner_id']",
    extra_trigger: ".o_sale_order",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "bottom",
    run: function (actions) {
        actions.text("Agrolait", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
}, {
    trigger: ".o_field_x2many_list_row_add > a",
    extra_trigger: ".o_sale_order",
    content: _t("Click here to add some products or services to your quotation."),
    position: "bottom",
}, {
    trigger: ".o_form_editable .o_field_many2one[name='product_id']",
    extra_trigger: ".o_sale_order",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: function (actions) {
        actions.text("Chair", this.$anchor.find("input"));
    },
}, {
    trigger: ".ui-menu-item > a",
    auto: true,
    in_modal: false,
    run: function (actions) {
        actions.auto();
        if ($('.modal-dialog:has(div.o_dialog_warning) footer.modal-footer .btn-primary').length) {
            $('.modal-dialog:has(div.o_dialog_warning) footer.modal-footer .btn-primary').trigger('click');
        }
    },
}, {
    trigger: ".o_form_button_save",
    extra_trigger: ".o_sale_order",
    content: _t("Once your quotation is ready, you can save, print or send it by email."),
    position: "right",
    id: "form_button_save_clicked"
}, {
    trigger: ".o_sale_print",
    extra_trigger: ".o_sale_order.o_form_readonly",
    content: _t("<b>Print this quotation to preview it.</b>"),
    position: "bottom"
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: ".o_sale_order [data-value='sent'].btn-primary",
    content: _t("Use the breadcrumbs to <b>go back to preceeding screens</b>."),
    position: "bottom"
}, {
    trigger: 'li a[data-menu-xmlid="sale.sale_order_menu"], .oe_secondary_menu_section[data-menu-xmlid="sale.sale_order_menu"]',
    content: _t("Use this menu to access quotations, sales orders and customers."),
    edition: "enterprise",
    position: "bottom"
}]);

});
