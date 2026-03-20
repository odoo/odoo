import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import * as tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_pricelist_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Azure Interior"),
        ...tourUtils.selectPricelist("Custom pricelist (TEST)"),
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        {
            content: "check price is correct (USD)",
            trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) span[name="sale_product_configurator_formatted_price"]:contains("750.00")',
        },
        configuratorTourUtils.increaseProductQuantity("Customizable Desk"),
        {
            content: "check price for 2",
            trigger: '.o_sale_product_configurator_table tr:has(span:contains("Customizable Desk")) td span[name="sale_product_configurator_formatted_price"]:contains("600.00")',
        },
        configuratorTourUtils.addOptionalProduct("Conference Chair (TEST)"),
        configuratorTourUtils.increaseProductQuantity("Conference Chair (TEST)"),
        configuratorTourUtils.addOptionalProduct("Chair floor protection (TEST)"),
        configuratorTourUtils.increaseProductQuantity("Chair floor protection (TEST)"),
        configuratorTourUtils.assertPriceTotal("1,257.00"),
        ...configuratorTourUtils.saveConfigurator(),
        {
            content: "verify SO final price excluded",
            trigger: 'span[name="Untaxed Amount"]:contains("1,257.00")',
            run: "click",
        },
        {
            content: "verify SO final price included",
            trigger: 'span[name="amount_total"]:contains("1,437.00")',
            run: "click",
        },
        ...stepUtils.saveForm()
    ]
});
