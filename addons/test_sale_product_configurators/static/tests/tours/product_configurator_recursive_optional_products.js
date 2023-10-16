/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_recursive_optional_products_tour', {
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
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1) label:contains("Aluminium")',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Conference Chair")) button:has(i.fa-shopping-cart)',
}, {
    trigger: 'tr:has(.o_sale_product_configurator_name:contains("Chair floor protection")) button:has(i.fa-shopping-cart)',
}, {
    trigger: 'button:contains(Confirm)',
}, ...stepUtils.discardForm()
]});
