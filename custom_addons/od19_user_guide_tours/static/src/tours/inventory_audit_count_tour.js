import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Inventory Audit Count Tour
 *
 * Walks the user through the physical stock count session:
 *  1. Open the Audit Counts list from the Inventory app
 *  2. Create a count session for a location
 *  3. Add the counted quantities on the lines
 *  4. Move the session forward (counted → approval → adjustment → reviewed)
 */
registry.category("web_tour.tours").add("od19_inventory_audit_count_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's run a <b>physical stock count</b> (Audit Counts)."))
        ),

        {
            trigger: navSection("Products"),
            content: markup(_t("Open the <b>Products</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Audit Counts"),
            content: markup(_t("Open <b>Audit Counts</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Stock Count Sessions"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line is a <b>count session</b>: it freezes the theoretical " +
                "quantities of one location so the team can count them on site."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to start a count session.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] input",
            content: markup(_t("Give the session a clear <b>name</b>, e.g. the period and the site.")),
            run: "edit Stock Count 2026-11 Warehouse",
        },
        {
            trigger: ".o_field_widget[name='location_id']",
            content: markup(_t(
                "Select the <b>location</b> to count. This is required and defines " +
                "which quants are frozen into the session."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='line_ids']",
            content: markup(_t(
                "The <b>lines</b> list every product of the location with its " +
                "<b>theoretical quantity</b>. Type the <b>counted quantity</b> next to each one."
            )),
            tooltipPosition: "top",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "When the count is finished, use <b>Mark as Counted</b>, then " +
                "<b>Submit for Approval</b>. A stock manager reviews the variances and " +
                "<b>Creates the Adjustment</b> to align the stock with reality."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),

        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Audit Count complete! Create a session → pick the location → enter the " +
                "counted quantities → <b>Mark as Counted</b> → <b>Submit for Approval</b> → " +
                "<b>Create Adjustment</b> → <b>Mark as Reviewed</b>."
            )),
            run: "click",
        },
    ],
});
