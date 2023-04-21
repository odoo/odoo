/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_optional_products_tour', {
    url: '/web',
    test: true,
    steps: [stepUtils.showAppsMenuItem(), {
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
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Office Chair Black")) button:has(i.fa-shopping-cart)',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Customizable Desk")) button:has(i.fa-plus)'
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Chair floor protection")) button:has(i.fa-shopping-cart)',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Conference Chair")) button:has(i.fa-shopping-cart)',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Conference Chair")) a:has(i.fa-trash-o)',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Conference Chair")) button:has(i.fa-shopping-cart)',
}, {
    trigger: 'button:contains(Confirm)',
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Customizable Desk")) td.o_data_cell:contains("2.0")',
    isCheck: true,
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Office Chair Black")) td.o_data_cell:contains("1.0")',
    isCheck: true,
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Conference Chair")) td.o_data_cell:contains("1.0")',
    isCheck: true,
}, {
    trigger: 'tr:has(td.o_data_cell:contains("Chair floor protection")) td.o_data_cell:contains("1.0")',
    isCheck: true,
}, ...stepUtils.discardForm()
]});
