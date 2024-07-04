/** @odoo-module **/

import { queryOne } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_single_custom_attribute_tour', {
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
    trigger: 'a:contains("Add a product")',
    run: "click",
}, {
    trigger: 'div[name="product_template_id"] input',
    run: "edit Custo",
}, {
    trigger: 'ul.ui-autocomplete a:contains("Customizable Desk (TEST)")',
    run: "click",
},
    configuratorTourUtils.setCustomAttribute("Customizable Desk (TEST)", "product attribute", "great single custom value"),
{
    trigger: ".modal button:contains(Confirm)",
    in_modal: false,
    run: "click",
},
{
    trigger: 'div[name="order_line"]',
},
{
    trigger: 'td.o_data_cell:contains("single product attribute value: great single custom value")',
}, {
    trigger: 'div[name="product_template_id"]',
    run: "click",
}, {
    trigger: '.fa-pencil',
    run: "click",
}, {
    trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] *:contains("Customizable Desk (TEST)")) td>div[name="ptal"]:has(div>label:contains("product attribute")) input[type="text"]',
    run: function () {
        // check custom value initialized
        if (
            queryOne(
                'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] *:contains("Customizable Desk (TEST)")) td>div[name="ptal"]:has(div>label:contains("product attribute")) input[type="text"]'
            ).value !== "great single custom value"
        ) {
            console.error("The value of custom product attribute should be 'great single custom value'.");
        }
    }
}, {
    trigger: 'button:contains("Cancel")',
    run: "click",
},
    ...stepUtils.discardForm()
]});
