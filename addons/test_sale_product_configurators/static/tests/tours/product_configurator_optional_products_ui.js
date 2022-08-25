/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('sale_product_configurator_optional_products_tour', {
    url: '/web',
    test: true,
}, [tour.stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order'
}, {
    trigger: 'a:contains("Add a product")',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
}, {
    trigger: 'tr:has(.td-product_name:contains("Office Chair Black")) .js_add',
}, {
    trigger: 'tr:has(.td-product_name:contains("Customizable Desk")) .fa-plus'
}, {
    trigger: 'tr:has(.td-product_name:contains("Chair floor protection")) .js_add',
}, {
    content: 'Is below its parent 1',
    trigger: 'tr:has(.td-product_name:contains("Office Chair Black")) + tr:has(.td-product_name:contains("Chair floor protection"))'
}, {
    trigger: 'tr:has(.td-product_name:contains("Conference Chair")) .js_add',
}, {
    trigger: 'tr:has(.td-product_name:contains("Conference Chair")) .fa-minus'
}, {
    trigger: 'tr:has(.td-product_name:contains("Chair floor protection")) .js_add',
}, {
    content: 'Is below its parent 2',
    trigger: 'tr:has(.td-product_name:contains("Conference Chair")) + tr:has(.td-product_name:contains("Chair floor protection"))'
}, {
    trigger: 'button span:contains(Confirm)',
    extra_trigger: '.oe_advanced_configurator_modal',
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Customizable Desk")) td.o_data_cell:contains("2.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Office Chair Black")) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Conference Chair")) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Chair floor protection")):nth(0) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Chair floor protection")):nth(1) td.o_data_cell:contains("1.0")',
    extra_trigger: 'div[name="order_line"]',
    run: function () {}, // check added product
}, ...tour.stepUtils.discardForm()
]);
