import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Purchase Jasper Reports Tour
 *
 * Walks the user through the legacy JasperReports ported from Odoo 15 that live
 * under Purchase > Reporting > Purchases Report (J-Report OD15):
 *  - (J-Report OD15) Purchase Order By Period
 *  - (J-Report OD15) Purchase Order Outstanding By Period
 *  - (J-Report OD15) Received Order By Period
 *
 * Each wizard opens with target="new", so there is no breadcrumb: the tour
 * waits for the dialog itself instead of using waitForAction().
 */
registry.category("web_tour.tours").add("od19_purchase_jasper_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "purchase.menu_purchase_root",
            markup(_t("Let's print the legacy <b>(J-Report OD15)</b> purchase reports."))
        ),
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Purchases Report (J-Report OD15)')",
            content: markup(_t("Open <b>Purchases Report (J-Report OD15)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Purchase Order By Period ---
        {
            trigger: navItem("(J-Report OD15) Purchase Order By Period"),
            content: markup(_t("Open <b>(J-Report OD15) Purchase Order By Period</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "The report wizard opens in a dialog. Pick the <b>language</b>, the " +
                "<b>date type</b> and the <b>period</b>, then press <b>Generate</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("Close the wizard — nothing is printed by accident.")),
            tooltipPosition: "top",
            run: "click",
        },

        // --- Purchase Order Outstanding By Period ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Reopen the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Purchases Report (J-Report OD15)')",
            content: markup(_t("Open <b>Purchases Report (J-Report OD15)</b> again.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("(J-Report OD15) Purchase Order Outstanding By Period"),
            content: markup(_t(
                "Open <b>(J-Report OD15) Purchase Order Outstanding By Period</b> — orders " +
                "not fully received yet."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t("Set the period, then press <b>Generate</b> to build the report.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("Close the wizard.")),
            tooltipPosition: "top",
            run: "click",
        },

        // --- Received Order By Period ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Reopen the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Purchases Report (J-Report OD15)')",
            content: markup(_t("Open <b>Purchases Report (J-Report OD15)</b> again.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("(J-Report OD15) Received Order By Period"),
            content: markup(_t("Open <b>(J-Report OD15) Received Order By Period</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t("Set the period, then press <b>Generate</b> to build the report.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("Close the wizard.")),
            tooltipPosition: "top",
            run: "click",
        },

        {
            trigger: ".o_menu_sections, .o_action_manager, .o_control_panel",
            content: markup(_t(
                "Purchase Jasper Reports tour complete! Every legacy (J-Report OD15) " +
                "purchase report uses this same wizard pattern."
            )),
            run: "click",
        },
    ],
});
