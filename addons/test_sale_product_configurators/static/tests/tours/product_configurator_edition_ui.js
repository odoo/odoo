import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_edition_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Tajine Saucisse"),
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Customizable Desk")) label:contains("Aluminium")',
            run: "click",
        },
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Customizable Desk (TEST) (Aluminium, White)"))',
        },
        ...configuratorTourUtils.saveConfigurator(),
        tourUtils.editLineMatching("Customizable Desk (TEST) (Aluminium, White)", ""),
        tourUtils.editConfiguration(),
        {
            // check updated legs
            trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) label:has(span:contains("Aluminium")) ~ input:checked',
        },
        {
            // check updated price
            trigger: '.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) span[name="sale_product_configurator_formatted_price"]:contains("800.40")',
        },
        {
            trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) label:has(span:contains("Custom")) ~ input',
            run: "click",
        },
        {
            trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) input[type="text"]',
            run: "edit nice custom value && click .modal-body",
        },
        {
            trigger:
                'tr:has(div[name="o_sale_product_configurator_name"]:contains("Customizable Desk")) label[style="background-color:#000000"] input:not(:visible)',
            run: "click",
        },
        {
            // used to sync with server
            trigger: 'div[name="o_sale_product_configurator_name"]:contains("Customizable Desk (TEST) (Custom, Black)")',
        },
        ...configuratorTourUtils.saveConfigurator(),
        tourUtils.editLineMatching("Customizable Desk (TEST) (Custom, Black)", "Custom: nice custom value"),
        tourUtils.editConfiguration(),
        configuratorTourUtils.setCustomAttribute("Customizable Desk", "Legs", "another nice custom value"),
        ...configuratorTourUtils.saveConfigurator(),
        tourUtils.editLineMatching("Customizable Desk (TEST) (Custom, Black)", "Custom: another nice custom value"),
        tourUtils.editConfiguration(),
        {
            trigger: 'table.o_sale_product_configurator_table tr:has(td>div[name="o_sale_product_configurator_name"] span:contains("Customizable Desk")) td>div[name="ptal"]:has(div>label:contains("Legs")) label:has(span:contains("Steel")) ~ input',
            run: "click",
        },
        configuratorTourUtils.assertProductNameContains("Customizable Desk (TEST) (Steel, Black)"),
        configuratorTourUtils.increaseProductQuantity("Customizable Desk"),
        // Mr Tajine Saucisse uses the pricelist that has a rule when 2 or more products. Price is 600
        configuratorTourUtils.assertPriceTotal("1,200.00"),
        ...configuratorTourUtils.saveConfigurator(),
        {
            // check quantity
            trigger: 'td.o_data_cell:contains("2.00")',
        },
        // make sure the custom value was removed on product change
        tourUtils.checkSOLDescriptionContains("Customizable Desk (TEST) (Steel, Black)", ""),
        ...stepUtils.saveForm(),
    ],
});
