import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("event_configurator_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Go to the Sales App"),
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("Azure"),
        ...tourUtils.addProduct("Event Registration"),
        {
            trigger: 'div[name="event_id"] input',
            run: "click",
        },
        {
            trigger: "ul.ui-autocomplete a:contains(/^Design Fair Los Angeles$/)",
            run: "click",
        },
        {
            trigger: 'div[name="event_ticket_id"] input',
            run: "click",
        },
        {
            trigger: "ul.ui-autocomplete a:contains(VIP)",
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
        ...tourUtils.clickSomewhereElse(),
        tourUtils.editLineMatching("Event Registration", "VIP"),
        tourUtils.editConfiguration(),
        {
            trigger: 'div[name="event_ticket_id"] input',
            run: "click",
        },
        {
            trigger: "ul.ui-autocomplete a:contains(Standard)",
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
        ...tourUtils.clickSomewhereElse(),
        tourUtils.checkSOLDescriptionContains("Event Registration", "Standard"),
        ...stepUtils.saveForm(),
    ],
});
