/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@test_sale_product_configurators/js/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_pricelist_tour', {
    url: '/web',
    test: true,
    steps: () => [
stepUtils.showAppsMenuItem(),
{
    content: "navigate to the sale app",
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    content: "create a new order",
    trigger: '.o_list_button_add',
    extra_trigger: ".o_sale_order"
}, {
    content: "search the partner",
    trigger: 'div[name="partner_id"] input',
    run: 'text Azure'
}, {
    content: "select the partner",
    trigger: 'ul.ui-autocomplete > li > a:contains(Azure)',
}, {
    content: "search the pricelist",
    trigger: 'input[id="pricelist_id_0"]',
    // Wait for onchange to come back
    extra_trigger: "[name=partner_id]:contains(Fremont)",
}, {
    content: "search the pricelist",
    trigger: 'input[id="pricelist_id_0"]',
    run: 'text Custo'
}, {
    content: "select the pricelist",
    trigger: 'ul.ui-autocomplete > li > a:contains(Custom pricelist (TEST))',
    in_modal: false,
}, {
    trigger: 'a:contains("Add a product")',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
}, {
    content: "check price is correct (USD)",
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(4) h5:contains("750.00")',
    isCheck: true,
}, {
    content: "add one more",
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(3)>div>button:has(i.fa-plus)',
}, {
    content: "check price for 2",
    trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(4) h5:contains("600.00")',
    isCheck: true,
},
    configuratorTourUtils.addOptionalProduct("Conference Chair"),
    configuratorTourUtils.increaseProductQuantity("Conference Chair"),
    configuratorTourUtils.addOptionalProduct("Chair floor protection"),
    configuratorTourUtils.increaseProductQuantity("Chair floor protection"),
    configuratorTourUtils.assertPriceTotal("1,257.00"),
{
    content: "add to SO",
    trigger: 'button:contains(Confirm)',
}, {
    content: "verify SO final price excluded",
    trigger: 'span[name="Untaxed Amount"]:contains("1,257.00")',
}, {
    content: "verify SO final price included",
    trigger: 'span[name="amount_total"]:contains("1,437.00")',
}, ...stepUtils.saveForm()
]});
