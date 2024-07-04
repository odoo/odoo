/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";

// Note: please keep this test without pricelist for maximum coverage.
// The pricelist is tested on the other tours.

registry.category("web_tour.tours").add('sale_product_configurator_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    run: "click",
}, 
{
    trigger: ".o_sale_order",
},
{
    trigger: '.o_list_button_add',
    run: "click",
}, {
    trigger: '.o_required_modifier[name=partner_id] input',
    run: "edit Tajine Saucisse",
}, {
    isActive: ["auto"],
    trigger: '.ui-menu-item > a:contains("Tajine Saucisse")',
    run: "click",
}, {
    trigger: 'a:contains("Add a product")',
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: "edit Custo",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    run: "click",
}, {
    trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) label:contains("Steel")',
    run: "click",
}, {
    trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) label:contains("Aluminium")',
    run: "click",
}, {
    trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) td[name="price"] span:contains("800.40")',
}, {
    trigger: 'label[style="background-color:#000000"] input',
    run: "click",
}, {
    trigger: '.btn-primary:disabled:contains("Confirm")',
    allowDisabled: true, // check confirm button is disabled
}, {
    trigger: 'label[style="background-color:#FFFFFF"] input',
    run: "click",
}, 
{
    trigger: ".modal-footer",
},
{
    trigger: '.btn-primary:not(:disabled):contains("Confirm")',
}, {
    trigger: '.o_sale_product_configurator_table_optional span:contains("Aluminium")',
    run: "click",
},
    configuratorTourUtils.addOptionalProduct("Conference Chair"),
    configuratorTourUtils.addOptionalProduct("Chair floor protection"),
{
    trigger: ".modal button:contains(Confirm)",
    in_modal: false,
    id: 'quotation_product_selected',
    run: "click",
},
// check that 3 products were added to the SO
{
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Aluminium, White)")',
}, {
    trigger: 'td.o_data_cell:contains("Conference Chair (TEST) (Aluminium)")',
},
// check that additional line is kept if selected but not edited with a click followed by a check
{
    trigger: 'td.o_data_cell:contains("Chair floor protection")',
    run: 'click',
}, {
    trigger: 'div[name="tax_totals"]',
    run: 'click',
}, {
    trigger: 'td.o_data_cell:contains("Chair floor protection")',
}, {
    trigger: 'span[name=amount_total]:contains("960.60")',
}, ...stepUtils.saveForm(),
]});
