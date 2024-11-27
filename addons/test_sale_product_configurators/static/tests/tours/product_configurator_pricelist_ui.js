import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_pricelist_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        {
            content: "search the partner",
            trigger: 'div[name="partner_id"] input',
            run: "edit Azure",
        },
        {
            content: "select the partner",
            trigger: 'ul.ui-autocomplete > li > a:contains(Azure)',
            run: "click",
        },
        {
            trigger: "[name=partner_id]:contains(Fremont)",
        },
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
        {
            content: "check price is correct (USD)",
            trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(3) span:contains("750.00")',
        },
        {
            content: "add one more",
            trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(4)>div>button:has(i.fa-plus)',
            run: "click",
        },
        {
            content: "check price for 2",
            trigger: 'main.modal-body>table:nth-child(1)>tbody>tr:nth-child(1)>td:nth-child(3) span:contains("600.00")',
        },
        configuratorTourUtils.addOptionalProduct("Conference Chair"),
        configuratorTourUtils.increaseProductQuantity("Conference Chair"),
        configuratorTourUtils.addOptionalProduct("Chair floor protection"),
        configuratorTourUtils.increaseProductQuantity("Chair floor protection"),
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
