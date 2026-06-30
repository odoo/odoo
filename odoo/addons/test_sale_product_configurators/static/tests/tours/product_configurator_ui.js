/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@test_sale_product_configurators/js/tour_utils";

// Note: please keep this test without pricelist for maximum coverage.
// The pricelist is tested on the other tours.

registry.category("web_tour.tours").add('sale_product_configurator_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
}, {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order'
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: 'text Tajine Saucisse',
}, {
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    auto: true,
}, {
    trigger: 'a:contains("Add a product")',
}, {
    trigger: 'div[name="product_template_id"] input',
    run: 'text Custo',
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
}, {
    trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) label:contains("Steel")',
    isCheck: true,
}, {
    trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) label:contains("Aluminium")',
}, {
    trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) td[name="price"] h5:contains("800.40")',
    isCheck: true, // check updated price
}, {
    trigger: 'label[style="background-color:#000000"] input'
}, {
    trigger: '.btn-primary:disabled:contains("Confirm")',
    isCheck: true, // check confirm button is disabled
}, {
    trigger: 'label[style="background-color:#FFFFFF"] input'
}, {
    trigger: '.btn-primary:not(:disabled):contains("Confirm")',
    extra_trigger: '.modal-footer',
    isCheck: true, // check confirm is available
}, {
    trigger: 'span:contains("Aluminium"):eq(1)',
},
    configuratorTourUtils.addOptionalProduct("Conference Chair"),
    configuratorTourUtils.addOptionalProduct("Chair floor protection"),
{
    trigger: 'button:contains(Confirm)',
    id: 'quotation_product_selected',
},
// check that 3 products were added to the SO
{
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Aluminium, White)")',
    isCheck: true,
}, {
    trigger: 'td.o_data_cell:contains("Conference Chair (TEST) (Aluminium)")',
    isCheck: true,
},
// check that additional line is kept if selected but not edited with a click followed by a check
{
    trigger: 'td.o_data_cell:contains("Chair floor protection")',
    run: 'click'
}, {
    trigger: 'div[name="tax_totals"]',
    run: 'click'
}, {
    trigger: 'td.o_data_cell:contains("Chair floor protection")',
    isCheck: true,
}, {
    trigger: 'span[name=amount_total]:contains("960.60")',
    isCheck: true,
}, ...stepUtils.saveForm(),
]});
