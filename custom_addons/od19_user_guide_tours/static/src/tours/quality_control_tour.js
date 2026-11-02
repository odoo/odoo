import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Quality Control Tour
 *
 * Walks the user through a quality inspection:
 *  1. Open the QC Inspections list from the Inventory app
 *  2. Create an inspection and pick the product
 *  3. Run it through the Pass / Fail workflow
 */
registry.category("web_tour.tours").add("od19_quality_control_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "stock.menu_stock_root",
            markup(_t("Let's run a <b>quality inspection</b> (QC Inspections)."))
        ),
        {
            trigger: navSection("Products"),
            content: markup(_t("Open the <b>Products</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("QC Inspections"),
            content: markup(_t("Open <b>QC Inspections</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("QC Inspections"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line is one inspection with its <b>type</b> (incoming / " +
                "outgoing / in-process) and its <b>status</b>."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to record an inspection.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='inspection_type'] .o_select_menu_toggler",
            content: markup(_t(
                "Choose the <b>Inspection Type</b>: incoming goods, outgoing " +
                "deliveries or an in-process check."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='product_id'] input",
            content: markup(_t("Pick the <b>product</b> to inspect (required).")),
            tooltipPosition: "bottom",
            run: "edit Communication",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains('Communication')",
            content: markup(_t("Select the product from the list.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='qty_tested'] input",
            content: markup(_t(
                "Under <b>Quantities</b> record how many units were <b>tested</b> and " +
                "how many were <b>accepted</b>; the rejected quantity is computed."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Use the status bar to move the inspection along: <b>Start</b> → " +
                "<b>Pass</b> / <b>Fail</b>. A failed inspection can spawn a " +
                "<b>nonconformity</b> in one click."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Quality Control tour complete! Inspections keep incoming and outgoing " +
                "goods under control."
            )),
            run: "click",
        },
    ],
});
