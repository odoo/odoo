import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Service Contract Tour
 *
 * Walks the user through the service-contract extension of the OCA contract
 * module (od19_service_contract):
 *  1. Open Accounting > Customers > Service Contracts
 *  2. Read the list of running service contracts
 *  3. Create a contract and review its Service tab (renewal, equipment, PM)
 */
registry.category("web_tour.tours").add("od19_service_contract_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's manage <b>Service Contracts</b> (สัญญาบริการ)."))
        ),
        {
            trigger: navSection("Customers"),
            content: markup(_t("Open the <b>Customers</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Service Contracts"),
            content: markup(_t("Open <b>Service Contracts</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Service Contracts"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Every line is a <b>service contract</b>: the customer, the recurring " +
                "amount and the contract status. Use the filters to spot expiring or " +
                "auto-renewing contracts."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to create a service contract.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            content: markup(_t(
                "Fill in the <b>customer</b>, the recurring lines and the contract dates. " +
                "The <b>Renew Contract</b> button appears in the header once the contract " +
                "is saved."
            )),
            run: "click",
        },
        {
            trigger: ".o_notebook .nav-link:text('Service')",
            content: markup(_t(
                "Open the <b>Service</b> tab: it holds the service-contract flags, the " +
                "renewal settings, the equipment under warranty and the preventive " +
                "maintenance cards."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='auto_renew']",
            content: markup(_t(
                "Tick <b>Auto Renew</b> and set the renewal interval (months) and the " +
                "notice (days) so the contract renews itself before it expires."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Service Contracts tour complete! Track warranty coverage and auto-renewal " +
                "straight from the contract."
            )),
            run: "click",
        },
    ],
});
