import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Sale Order Print (Native QWeb) Tour
 *
 * Walks the user through the native QWeb replacement of the legacy Jasper
 * "sale order print" report. The old "Sale Order Print (Test)" menu entry was
 * removed when the OD19 menus were consolidated, so the reports are reached the
 * standard way: open a sale order and use its <b>Print</b> menu (each report is
 * bound to sale.order with binding_type = "report").
 *  1. Open Sales > Orders > Orders
 *  2. Open a sale order
 *  3. Print a native report from the Print menu
 */
registry.category("web_tour.tours").add("od19_sale_report_native_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "sale.sale_menu_root",
            markup(_t("Let's print a sale order with the <b>native QWeb</b> reports."))
        ),

        {
            trigger: navSection("Orders"),
            content: markup(_t("Open the <b>Orders</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Orders"),
            content: markup(_t("Open <b>Orders</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Orders"),
        {
            trigger: ".o_list_renderer .o_data_row:first .o_data_cell:first",
            content: markup(_t("Click a sale order to open it.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_statusbar",
            content: markup(_t(
                "Open the <b>Print</b> action menu (printer icon of the control panel) and pick a " +
                "report: <b>Sale Order (Classic)</b>, <b>Sale Order (Modern)</b> or any of the Thai " +
                "variants (มินิมอล, องค์กร, เรียบหรู, ...). Every report is rendered by QWeb, so it " +
                "no longer needs Jasper or jasperstarter."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Sale Order Print complete! Open an order and print it from the <b>Print</b> " +
                "menu — fully native, in Thai, with the company layout."
            )),
            run: "click",
        },
    ],
});
