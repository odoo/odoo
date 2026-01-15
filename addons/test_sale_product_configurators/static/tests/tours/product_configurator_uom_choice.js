import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_uom_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer('Tajine Saucisse'),
        {
            content: "search the pricelist",
            trigger: 'input[id="pricelist_id_0"]',
            // Wait for onchange to come back
            run: "edit Test",
        },
        {
            content: "search the pricelist",
            trigger: 'input[id="pricelist_id_0"]',
            run: "edit Custo",
        },
        {
            content: "select the pricelist",
            trigger: 'ul.ui-autocomplete > li > a:contains(Custom pricelist (TEST))',
            run: "click",
        },
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        configuratorTourUtils.assertProductPrice("Customizable Desk (TEST)", "750.00"),
        configuratorTourUtils.increaseProductQuantity("Customizable Desk (TEST)"),
        configuratorTourUtils.assertProductPrice("Customizable Desk (TEST)", "600.00"),
        configuratorTourUtils.decreaseProductQuantity("Customizable Desk (TEST)"),
        configuratorTourUtils.assertProductPrice("Customizable Desk (TEST)", "750.00"),
        configuratorTourUtils.setProductUoM("Customizable Desk (TEST)", "Dozens"),
        configuratorTourUtils.assertProductPrice("Customizable Desk (TEST)", "7,200.00"),
        configuratorTourUtils.addOptionalProduct("Conference Chair"),
        configuratorTourUtils.assertProductPrice("Conference Chair", "16.50"),
        configuratorTourUtils.increaseProductQuantity("Conference Chair"),
        configuratorTourUtils.assertProductPrice("Conference Chair", "16.50"),
        configuratorTourUtils.setProductUoM("Conference Chair", "Dozens"),
        configuratorTourUtils.assertProductPrice("Conference Chair", "198.00"),
        configuratorTourUtils.addOptionalProduct("Chair floor protection"),
        configuratorTourUtils.assertProductPrice("Chair floor protection", "12.00"),
        configuratorTourUtils.increaseProductQuantity("Chair floor protection"),
        configuratorTourUtils.assertPriceTotal("7,620.00"),
        ...configuratorTourUtils.saveConfigurator(),
        {
            content: "verify SO final price excluded",
            trigger: 'span[name="Untaxed Amount"]:contains("7,620.00")',
            run: "click",
        },
        {
            content: "verify SO final price included",
            trigger: 'span[name="amount_total"]:contains("8,700.00")',
            run: "click",
        },
        ...stepUtils.saveForm()
    ]
});
