import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Stock Card (J-Report OD15) Tour
 *
 * Walks the user through one of the legacy JasperReports ported from Odoo 15:
 *  1. Open Reporting > Stock Reports (J-Report OD15) from the Inventory app
 *  2. Open the (J-Report OD15) Stock Card wizard
 *  3. Pick the parameters (language, date option, warehouse, products)
 *
 * The wizard opens with target="new", so there is no breadcrumb: the tour waits
 * for the dialog itself instead of using waitForAction().
 */
registry.category("web_tour.tours").add("od19_stock_jasper_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's print a legacy <b>(J-Report OD15) Stock Card</b>."))
        ),
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("(J-Report OD15) Stock Card"),
            content: markup(_t(
                "Open <b>(J-Report OD15) Stock Card</b> (Reporting ▸ Stock Reports " +
                "(J-Report OD15))."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "The report wizard opens in a dialog. Every legacy Jasper report shares this " +
                "layout: pick the parameters, then press <b>Generate</b>."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_dialog .o_field_widget[name='date_option']",
            content: markup(_t(
                "Choose the <b>date option</b> — a single date, a range or an as-of date — to " +
                "scope the movements. The matching date fields appear automatically."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_dialog .o_field_widget[name='wh']",
            content: markup(_t("Select the <b>warehouse</b> to analyse.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_dialog .o_field_widget[name='p_Product']",
            content: markup(_t(
                "Optionally restrict the report to specific <b>products</b> or product " +
                "<b>categories</b>."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t(
                "Close the wizard with <b>Close</b> — the tour leaves it unsaved so nothing is " +
                "printed by accident."
            )),
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: ".o_main_navbar",
            content: markup(_t(
                "Stock Card (J-Report OD15) tour complete! Every legacy Jasper report uses the " +
                "same wizard pattern."
            )),
        },
    ],
});
