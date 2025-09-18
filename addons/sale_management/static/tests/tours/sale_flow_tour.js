import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";
import tourUtils from "@sale/js/tours/tour_utils";

registry.category("web_tour.tours").add("test_basic_sale_flow_with_minimal_access_rights", {
    steps: () => [
        ...stepUtils.goToAppSteps("sale.sale_menu_root", "Open the sales app"),
        {
            content: "Check that at least one quotation is present in the view",
            trigger: ".o_sale_onboarding_list_view .o_data_row",
        },
        ...tourUtils.createNewSalesOrder(),
        ...tourUtils.selectCustomer("partner_a"),
        ...tourUtils.addProduct("Test Product"),
        tourUtils.checkSOLDescriptionContains("Test Product"),
        {
            trigger: "button[name=action_confirm]",
            run: "click",
        },
        {
            trigger: ".o_statusbar_status .o_arrow_button_current:contains(Sales Order)",
        },
        {
            trigger: "button[id=create_invoice]",
            run: "click",
        },
        {
            trigger: ".modal-content button[id=create_invoice_open]",
            run: "click",
        },
        {
            content: "Check that we are in the invoice form view",
            trigger: ".o_statusbar_status:contains(Posted) .o_arrow_button_current:contains(Draft)",
        },
        {
            content: "Check that the invoice is linked to the sale order",
            trigger: "button[name=action_view_source_sale_orders] .o_stat_value:contains(1)",
        },
    ],
});
