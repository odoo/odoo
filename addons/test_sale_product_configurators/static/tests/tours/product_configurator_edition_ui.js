/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@test_sale_product_configurators/js/tour_utils";
import { queryAll, queryOne } from "@odoo/hoot-dom";

registry.category("web_tour.tours").add('sale_product_configurator_edition_tour', {
    url: '/web',
    test: true,
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
    run: "click",
}, {
    trigger: '.o_list_button_add',
    extra_trigger: '.o_sale_order',
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
    trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Customizable Desk")) label:contains("Aluminium")',
    run: "click",
}, {
    trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Customizable Desk (TEST) (Aluminium, White)"))',
}, {
    trigger: 'button:contains(Confirm)',
    run: "click",
}, {
    // check added product
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Aluminium, White)")',
    extra_trigger: 'div[name="order_line"]',
}, {
    trigger: 'div[name="product_template_id"]',
    run: "click",
}, {
    trigger: '.fa-pencil',
    run: "click",
}, {
    // check updated legs
    trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) label:has(span:contains("Aluminium")) ~ input:checked',
}, {
    // check updated price
    trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) td[name="price"] h5:contains("800.40")',
}, {
    trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) label:has(span:contains("Custom")) ~ input',
    run: "click",
}, {
    trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) input[type="text"]',
    run: "edit nice custom value && click .modal-body",
}, {
    trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Customizable Desk")) label[style="background-color:#000000"] input',
    run: "click", 
}, {
    // used to sync with server
    trigger: 'div[name="o_sale_product_configurator_name"]:contains("Customizable Desk (TEST) (Custom, Black)")',
}, {
    trigger: 'button:contains(Confirm)',
    run: "click",
}, {
    // check updated product
    trigger: 'td.o_data_cell:contains("Customizable Desk (TEST) (Custom, Black)")',
    extra_trigger: 'div[name="order_line"]',
}, {
    // check custom value
    trigger: 'td.o_data_cell:contains("Custom: nice custom value")',
    extra_trigger: 'div[name="order_line"]',
}, {
    trigger: 'div[name="product_template_id"]',
    run: "click",
}, {
    trigger: '.fa-pencil',
    run: "click",
},
    configuratorTourUtils.setCustomAttribute("Customizable Desk", "Legs", "another nice custom value"),
{
    trigger: 'button:contains(Confirm)',
    run: "click",
}, {
    // check custom value
    trigger: 'td.o_data_cell:contains("Custom: another nice custom value")',
    extra_trigger: 'div[name="order_line"]',
}, {
    trigger: 'div[name="product_template_id"]',
    run: "click",
}, {
    trigger: '.fa-pencil',
    run: "click",
}, {
    trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] h5:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) label:has(span:contains("Steel")) ~ input',
    run: "click",
},
    configuratorTourUtils.assertProductNameContains("Customizable Desk (TEST) (Steel, Black)"),
    configuratorTourUtils.increaseProductQuantity("Customizable Desk"),
    // Mr Tajine Saucisse uses the pricelist that has a rule when 2 or more products. Price is 600
    configuratorTourUtils.assertPriceTotal("1,200.00"),
{
    trigger: 'button:contains(Confirm)',
    run: "click",
}, {
    // check quantity
    trigger: 'td.o_data_cell:contains("2.00")',
}, {
    trigger: 'div[name="product_template_id"]',
    run: function () {
        // used to check that the description does not contain a custom value anymore
        if (queryAll(`td.o_data_cell:contains("Custom: another nice custom value")`).length === 0){
            const el = queryOne(
                'td.o_data_cell:contains("Customizable Desk (TEST) (Steel, Black)")'
            )
            el.textContent = "tour success";
        }
    }
}, {
    trigger: 'td.o_data_cell:contains("tour success")',
    extra_trigger: 'div[name="order_line"]',
},
    ...stepUtils.saveForm(),
]});
