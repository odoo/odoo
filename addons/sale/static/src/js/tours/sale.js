odoo.define('sale.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('sale_tour', {
    url: "/web",
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Open Sales app to send your first quotation in a few clicks.'),
    position: 'right',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    content: _t('Open Sales app to send your first quotation in a few clicks.'),
    position: 'bottom',
    edition: 'enterprise'
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order",
    content: _t("Let's create a new quotation.<br/><i>Note that colored buttons usually point to the next logical actions.</i>"),
    position: "bottom",
}, {
    trigger: ".o_form_editable .o_field_many2one[name='partner_id'] input",
    extra_trigger: ".o_sale_order",
    content: _t("Write the name of your customer to create one on the fly, or select an existing one."),
    position: "bottom",
    run: 'text Agrolait'
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
    trigger: ".o_field_widget[name=product_id] input, .o_field_widget[name=product_template_id] input",
    extra_trigger: ".o_sale_order",
    content: _t("Select a product, or create a new one on the fly."),
    position: "right",
    run: function (actions) {
        var $input = this.$anchor.find('input');
        actions.text("DESK0001", $input.length === 0 ? this.$anchor : $input);
        // fake keydown to trigger search
        var keyDownEvent = jQuery.Event("keydown");
        keyDownEvent.which = 42;
        this.$anchor.trigger(keyDownEvent);
        var $descriptionElement = $('.o_form_editable textarea[name="name"]');
        // when description changes, we know the product has been created
        $descriptionElement.change(function () {
            $descriptionElement.addClass('product_creation_success');
        });
    },
    id: 'product_selection_step'
}, {
    trigger: '.o_m2o_dropdown_option a:contains("DESK0001")'
}, {
    trigger: '.o_form_editable textarea[name="name"].product_creation_success',
    run: function () {} // wait for product creation
}, {
    trigger: ".o_form_button_save",
    extra_trigger: ".o_sale_order",
    content: _t("Once your quotation is ready, you can save, print or send it by email."),
    position: "right",
    id: "form_button_save_clicked"
}, {
    trigger: ".breadcrumb-item:not(.active):last",
    extra_trigger: ".o_sale_order [data-value='draft'].btn-primary",
    content: _t("Use the breadcrumbs to <b>go back to preceeding screens</b>."),
    position: "bottom"
}, {
    trigger: 'li a[data-menu-xmlid="sale.sale_order_menu"], .oe_secondary_menu_section[data-menu-xmlid="sale.sale_order_menu"]',
    content: _t("Use this menu to access quotations, sales orders and customers."),
    edition: "enterprise",
    position: "bottom"
}]);

});
