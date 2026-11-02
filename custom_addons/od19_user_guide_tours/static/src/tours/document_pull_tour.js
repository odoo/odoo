import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Document Pull Tour
 *
 * Walks the user through the GRNI (Goods Received Not Invoiced) report that
 * backs the period-end accrual:
 *  1. Open Reporting from the Purchase app
 *  2. Open the GRNI report
 *  3. Read received vs invoiced quantities and the quantity still to invoice
 */
registry.category("web_tour.tours").add("od19_document_pull_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase.menu_purchase_root",
            markup(_t("Let's review the goods received but not yet invoiced (<b>GRNI</b>)."))
        ),
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("GRNI / ของรับแล้วยังไม่วางบิล"),
            content: markup(_t(
                "Open <b>GRNI</b> — the report of received products that the vendor has not " +
                "billed yet."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("GRNI (Received Not Invoiced) / ของรับแล้วยังไม่วางบิล"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line shows the <b>order</b>, <b>vendor</b>, <b>product</b>, the planned " +
                "date, and the quantities <b>received</b> vs <b>invoiced</b> — plus the quantity " +
                "still <b>to invoice</b>, which is the accrual to book at period end."
            )),
            run: "click",
        },
    ],
});
