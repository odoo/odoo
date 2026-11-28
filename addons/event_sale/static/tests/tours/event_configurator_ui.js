import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import * as tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("event_configurator_tour", {
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
            trigger: "ul.ui-autocomplete a:text(Design Fair Los Angeles)",
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
        tourUtils.editConfiguration("VIP"),
        {
            trigger: 'div[name="event_ticket_id"] input',
            run: "click",
        },
        {
            trigger: "ul.ui-autocomplete a:contains(Standard)",
            run: "click",
        },
        {
            content: "No option is ticked by default, tick Lunch",
            trigger: ".modal div[name='ticket_option_product_ids'] .form-check:contains(Lunch) input:not(:checked)",
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
        tourUtils.checkSOLDescriptionContains("Standard", "Design Fair Los Angeles"),
        {
            content: "The ticked option is added as a line of the order",
            trigger: ".o_field_sol_label_text:contains(Lunch)",
        },
        ...stepUtils.saveForm(),
    ],
});
