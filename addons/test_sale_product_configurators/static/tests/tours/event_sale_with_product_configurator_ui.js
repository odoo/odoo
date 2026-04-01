import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import configuratorTourUtils from "@sale/js/tours/product_configurator_tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("event_sale_with_product_configurator_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Tajine Saucisse"),
        ...tourUtils.addProduct("Registration Event (TEST variants)"),
        {
            trigger:
            'tr:has(div[name="o_sale_product_configurator_name"]:contains("Memorabilia")) button:has(i.oi-plus)',
            run: "click",
        },
        {
            trigger: ".modal button:contains(Confirm)",
            run: "click",
        },
        {
            trigger: ".modal .o_input_dropdown input",
            run: "edit Test",
        },
        {
            trigger: '.modal ul.ui-autocomplete a:contains("TestEvent")',
            run: "click",
        },
        {
            trigger: '.modal div[name="event_ticket_id"] input',
            run: "click",
        },
        {
            trigger: '.modal ul.ui-autocomplete a:contains("Kid + meal")',
            run: "click",
        },
        {
            trigger: ".modal .o_event_sale_js_event_configurator_ok",
            run: "click",
        },
        {
            content: "Wait the modal is closed",
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: 'td[name="price_subtotal"]:contains("16.50")', // wait for the optional product line
        },
        ...tourUtils.addProduct("Registration Event (TEST variants)"),
        {
            trigger:
            'tr:has(div[name="o_sale_product_configurator_name"]:contains("Registration Event (TEST variants)")) label:contains("Adult")',
            run: "click",
        },
        {
            trigger:
            'tr:has(div[name="o_sale_product_configurator_name"]:contains("Registration Event (TEST variants)")) .o_sale_product_configurator_qty input',
            run: "edit 5 && click body",
        },
        configuratorTourUtils.assertPriceTotal("150.00"),
        {
            trigger: ".modal button:contains(Confirm)",
            run: "click",
        },
        {
            trigger: ".modal .o_input_dropdown input",
            run: "edit Test",
        },
        {
            trigger: '.modal ul.ui-autocomplete a:contains("TestEvent")',
            run: "click",
        },
        {
            trigger: '.modal div[name="event_ticket_id"] input',
            run: "click",
        },
        {
            trigger: '.modal ul.ui-autocomplete a:contains("Adult")',
            run: "click",
        },
        {
            trigger: ".modal .o_event_sale_js_event_configurator_ok",
            run: "click",
        },
        {
            content: "Wait the modal is closed",
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: 'td[name="price_subtotal"]:contains("150.00")', // wait for the adult tickets line
        },
        ...tourUtils.addProduct("Registration Event (TEST variants)"),
        {
            trigger:
            'tr:has(div[name="o_sale_product_configurator_name"]:contains("Registration Event (TEST variants)")) label:contains("VIP")',
            run: "click",
        },
        configuratorTourUtils.assertPriceTotal(60.0),
        {
            trigger: ".modal button:contains(Confirm)",
            run: "click",
        },
        {
            trigger: ".modal .o_input_dropdown input",
            run: "edit Test",
        },
        {
            trigger: '.modal ul.ui-autocomplete a:contains("TestEvent")',
            run: "click",
        },
        {
            trigger: '.modal div[name="event_ticket_id"] input',
            run: "click",
        },
        {
            trigger: '.modal ul.ui-autocomplete a:contains("VIP")',
            run: "click",
        },
        {
            trigger: ".modal .o_event_sale_js_event_configurator_ok",
            run: "click",
        },
        {
            content: "Wait the modal is closed",
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: '.o_field_cell.o_data_cell.o_list_number:contains("60.00")',
        },
        ...stepUtils.saveForm(),
    ],
});
