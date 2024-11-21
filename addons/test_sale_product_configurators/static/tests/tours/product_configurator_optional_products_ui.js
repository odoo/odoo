/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add('sale_product_configurator_optional_products_tour', {
    url: '/odoo',
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Tajine Saucisse"),
        ...tourUtils.addProduct("Customizable Desk (TEST)"),
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Office Chair Black")) button:has(i.fa-plus)',
            run: "click",
        },
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Customizable Desk")) button:has(i.fa-plus)',
            run: "click",
        },
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Chair floor protection")) button:has(i.fa-plus)',
            run: "click",
        },
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Conference Chair")) button:has(i.fa-plus)',
            run: "click",
        },
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Conference Chair")) a:contains("Remove")',
            run: "click",
        },
        {
            trigger: 'tr:has(div[name="o_sale_product_configurator_name"]:contains("Conference Chair")) button:has(i.fa-plus)',
            run: "click",
        },
        {
            trigger: ".modal button:contains(Confirm)",
            run: "click",
        },
        {
            trigger: ".modal-title:contains(Warning for Conference Chair (TEST))",
        },
        {
            trigger: '.o-default-button',
            run: "click",
        },
        {
            trigger: 'tr:has(td.o_data_cell:contains("Customizable Desk")) td.o_data_cell:contains("2.0")',
        },
        {
            trigger: 'tr:has(td.o_data_cell:contains("Office Chair Black")) td.o_data_cell:contains("1.0")',
        },
        {
            trigger: 'tr:has(td.o_data_cell:contains("Conference Chair")) td.o_data_cell:contains("1.0")',
        },
        {
            trigger: 'tr:has(td.o_data_cell:contains("Chair floor protection")) td.o_data_cell:contains("1.0")',
        },
        ...stepUtils.saveForm()
    ],
});
