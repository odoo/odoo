import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sale Order Print (Native QWeb) Tour
 *
 * Walks the user through the native QWeb replacement of the legacy Jasper
 * "sale order print" report:
 *  1. Open Sales > Reporting > Sale Order Print (Test)
 *  2. Open a sale order
 *  3. Print the native report
 */
registry.category("web_tour.tours").add("od19_sale_report_native_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's print a sale order with the <b>native QWeb</b> report."))
        ),

        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("รายงานพิมพ์ใบสั่งขาย (ทดสอบ)"),
            content: markup(_t(
                "Open <b>รายงานพิมพ์ใบสั่งขาย (ทดสอบ) / Sale Order Print (Test)</b> — " +
                "the test entry of the native report."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("รายงานพิมพ์ใบสั่งขาย (ทดสอบ) / Sale Order Print (Test)"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t("Open a sale order to print it.")),
        },
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("Click a sale order to open it.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_statusbar",
            content: markup(_t(
                "Inside the sale order use <b>Print</b> (the printer icon of the action " +
                "menu) and pick <b>รายงานพิมพ์ใบสั่งขาย</b>. The report is rendered by " +
                "QWeb, so it no longer needs Jasper or jasperstarter."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Sale Order Print complete! Open Sales &gt; Reporting &gt; " +
                "<b>รายงานพิมพ์ใบสั่งขาย (ทดสอบ)</b>, open an order and print it from the " +
                "<b>Print</b> menu — fully native, in Thai, with the company layout."
            )),
            run: "click",
        },
    ],
});
