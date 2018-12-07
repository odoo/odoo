odoo.define('sale.product_configurator_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

tour.register('sale_product_configurator_tour', {
    url: "/web",
    test: true,
}, [tour.STEPS.SHOW_APPS_MENU_ITEM, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'community'
}, {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    edition: 'enterprise'
}, {
    trigger: ".o_list_button_add",
    extra_trigger: ".o_sale_order"
}, {
    trigger: ".o_required_modifier[name=partner_id] input",
    run: "text Couscous Magique",
}, {
    trigger: ".ui-menu-item > a:contains('Couscous Magique')",
    auto: true,
}, {
    trigger: "a:contains('Configure a product')",
    extra_trigger: ".o_field_widget[name=pricelist_id] > .o_external_button", // Wait for pricelist (onchange_partner_id)
}, {
    trigger: '.o_product_configurator .o_input_dropdown input',
    run: 'click'
}, {
    trigger: 'li a:contains("Customizable Desk")',
    in_modal: false,
    extra_trigger: 'ul.ui-autocomplete',
    run: 'click'
}, {
    trigger: '.configurator_container span:contains("Steel")',
    run: function () {
        $('input.product_id').change(function () {
            var request_count = 0;
            if ($('.o_sale_product_configurator_add').attr('request_count')) {
                request_count = parseInt($('.o_sale_product_configurator_add').attr('request_count'));
            }
            request_count++;
            $('.o_sale_product_configurator_add').attr('request_count', request_count);
        });
    }
}, {
    trigger: '.configurator_container span:contains("Aluminium")',
    run: 'click'
}, {
    trigger: 'span.oe_currency_value:contains("800")',
    run: function (){} // check updated price
}, {
    trigger: 'input[data-value_name="Black"]'
}, {
    trigger: 'input[data-value_name="White"]'
}, {
    trigger: '.o_sale_product_configurator_add[request_count="3"]',
    run: function (){} // used to sync with "get_combination_info" completion
}, {
    trigger: '.o_sale_product_configurator_add:not(.disabled)'
}, {
    trigger: 'span:contains("Aluminium")',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
}, {
    trigger: '.js_product:has(strong:contains(Conference Chair)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Conference Chair))',
    run: 'click'
}, {
    trigger: '.js_product:has(strong:contains(Chair floor protection)) .js_add',
    extra_trigger: '.oe_optional_products_modal .js_product:has(strong:contains(Chair floor protection))',
    run: 'click'
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_optional_products_modal',
    run: 'click'
},
// check that 3 products were added to the SO
{
    trigger: 'td.o_data_cell:contains("Customizable Desk (White, Aluminium)")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){}
}, {
    trigger: 'td.o_data_cell:contains("Conference Chair (Aluminium)")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){}
}, {
    trigger: 'td.o_data_cell:contains("Chair floor protection")',
    extra_trigger: 'div[name="order_line"]',
    in_modal: false,
    run: function (){}
}, {
    trigger: '.o_readonly_modifier[name=amount_total]:contains("835")',
    in_modal: false,
    edition: 'community',
    run: function (){}
}, {
    trigger: '.o_readonly_modifier[name=amount_total]:contains("837")',
    in_modal: false,
    edition: 'enterprise',
    run: function (){}
}]);

});
