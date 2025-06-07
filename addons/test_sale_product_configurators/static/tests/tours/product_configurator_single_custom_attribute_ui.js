/** @odoo-module **/

import { queryOne } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_single_custom_attribute_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        configuratorTourUtils.setCustomAttribute("Customizable Desk (TEST)", "product attribute", "great single custom value"),
        ...configuratorTourUtils.saveConfigurator(),
        tourUtils.editLineMatching("Customizable Desk (TEST)", "single product attribute value: great single custom value"),
        tourUtils.editConfiguration(),
        {
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
        },
        {
            trigger: '.modal button:contains("Cancel")',
            run: "click",
        },
        ...stepUtils.discardForm(),
    ],
});
