import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Accounting Clearing Wizards Tour
 *
 * Walks the user through the four clearing wizards of od19_accounting_features,
 * all reachable from Accounting > Accounting (the "Accounting" section):
 *  - Period Clearing          (period-end open items)
 *  - VAT Clearing (ภ.พ.30)    (output/input VAT settlement)
 *  - WHT Clearing             (withholding tax settlement)
 *  - Suspense / Intercompany  (บัญชีพัก / intercompany)
 *
 * Every wizard opens with target="new", so there is no breadcrumb: the tour
 * waits for the dialog itself instead of using waitForAction().
 */
registry.category("web_tour.tours").add("od19_accounting_clearing_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's clear the period, VAT, WHT and suspense accounts."))
        ),
        {
            trigger: navSection("Accounting"),
            content: markup(_t("Open the <b>Accounting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- Period Clearing ---
        {
            trigger: navItem("Period Clearing"),
            content: markup(_t("Open <b>Period Clearing</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "Set the <b>date range</b> and the accounts, then press " +
                "<b>Load Open Items</b> to list what is left unreconciled; " +
                "<b>Reconcile</b> clears it."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("Close the wizard without clearing.")),
            tooltipPosition: "top",
            run: "click",
        },

        // --- VAT Clearing (ภ.พ.30) ---
        {
            trigger: navSection("Accounting"),
            content: markup(_t("Reopen the <b>Accounting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("VAT Clearing (ภ.พ.30)"),
            content: markup(_t("Open <b>VAT Clearing (ภ.พ.30)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "Pick the <b>date</b>, the <b>journal</b> and the output / input VAT " +
                "accounts. The net VAT payable or refundable is computed, then " +
                "<b>Clear &amp; Reconcile</b> settles it."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("Close the wizard.")),
            tooltipPosition: "top",
            run: "click",
        },

        // --- WHT Clearing ---
        {
            trigger: navSection("Accounting"),
            content: markup(_t("Reopen the <b>Accounting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("WHT Clearing (ภาษีหัก ณ ที่จ่าย)"),
            content: markup(_t("Open <b>WHT Clearing (ภาษีหัก ณ ที่จ่าย)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "Choose the withholding accounts and the settlement account. Tick " +
                "<b>Post settlement</b> to create the settlement entry, then " +
                "<b>Clear &amp; Reconcile</b>."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog footer button[special='cancel']",
            content: markup(_t("Close the wizard.")),
            tooltipPosition: "top",
            run: "click",
        },

        // --- Suspense / Intercompany Clearing ---
        {
            trigger: navSection("Accounting"),
            content: markup(_t("Reopen the <b>Accounting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("Suspense / Intercompany Clearing (บัญชีพัก)"),
            content: markup(_t("Open <b>Suspense / Intercompany Clearing (บัญชีพัก)</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_dialog .modal-title",
            timeout: 20000,
            content: markup(_t(
                "Select the <b>suspense</b> and <b>intercompany</b> accounts, " +
                "<b>Load Open Items</b> and clear the parked balances."
            )),
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
                "Accounting Clearing tour complete! Period, VAT, WHT and suspense balances " +
                "are cleared from these four wizards."
            )),
            run: "click",
        },
    ],
});
