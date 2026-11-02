import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, navItem } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Thai Tax Reports Tour
 *
 * Walks the user through generating Thai statutory tax reports:
 *  - VAT Sales Register (สมุดรายการภาษีขาย)
 *  - VAT Purchase Register (สมุดรายการภาษีซื้อ)
 *  - WHT Register (สมุดภาษีหัก ณ ที่จ่าย)
 */
registry.category("web_tour.tours").add("od19_thai_tax_reports_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "account.menu_finance",
            markup(_t("Let's generate <b>Thai Tax Reports</b> (VAT and WHT registers)."))
        ),

        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Thai Tax Reports')",
            content: markup(_t("Open the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },

        // --- VAT Sales Register ---
        {
            trigger: navItem("VAT Sales Register (สมุดรายการภาษีขาย)"),
            content: markup(_t(
                "Open <b>VAT Sales Register (สมุดรายการภาษีขาย)</b> for output VAT."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='date_from'] .o_input, .o_field_widget[name='start_date'] .o_input, .modal .o_datepicker .o_input",
            content: _t("Set the start date of the reporting period."),
        },
        {
            trigger: ".o_field_widget[name='date_to'] .o_input, .o_field_widget[name='end_date'] .o_input",
            content: _t("Set the end date of the reporting period."),
        },
        {
            trigger: "button[name='action_print'], button:contains('Print'), button:contains('Generate')",
            content: markup(_t("Click <b>Print/Generate</b> to produce the VAT Sales Register.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Printing a register opens a dialog asynchronously: the
        // "Configure your document layout" configurator when no layout has
        // been saved yet, or an "Invalid Operation" warning when the period
        // has no data. Target a *visible* element: the `.o_dialog` wrapper has
        // no box of its own, so a `visible:true` query never matches it (that
        // is why the previous `:has()`-on-`.o_dialog` trigger never fired).
        // A step without run is never blocked by a modal, so it can safely
        // wait for the dialog, and the guarded close below is evaluated only
        // once the dialog is rendered.
        {
            trigger: "button[name='document_layout_save'], .o_error_dialog .o-default-button, .o_dialog .modal-title",
            timeout: 30000,
        },
        {
            isActive: [".o_dialog .modal-header .btn-close"],
            trigger: ".o_dialog .modal-header .btn-close",
            content: markup(_t("Close the warning / document layout dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            // `action_print()` hands the browser a report action: when no
            // document layout is saved yet Odoo first shows the "Configure your
            // document layout" dialog, and once it is closed the report is
            // streamed and the action manager is left EMPTY — there is no
            // form/list/kanban to wait for. Wait for the app navbar, which is
            // always mounted, so the tour can carry on to the next register.
            trigger: ".o_menu_sections, .o_control_panel, .o_action_manager",
        },

        // --- VAT Purchase Register ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Thai Tax Reports')",
            content: markup(_t("Go back to the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("VAT Purchase Register (สมุดรายการภาษีซื้อ)"),
            content: markup(_t(
                "Open <b>VAT Purchase Register (สมุดรายการภาษีซื้อ)</b> for input VAT."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button[name='action_print'], button:contains('Print'), button:contains('Generate')",
            content: markup(_t("Set the period and click <b>Print/Generate</b>.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Printing a register opens a dialog asynchronously: the
        // "Configure your document layout" configurator when no layout has
        // been saved yet, or an "Invalid Operation" warning when the period
        // has no data. Target a *visible* element: the `.o_dialog` wrapper has
        // no box of its own, so a `visible:true` query never matches it (that
        // is why the previous `:has()`-on-`.o_dialog` trigger never fired).
        // A step without run is never blocked by a modal, so it can safely
        // wait for the dialog, and the guarded close below is evaluated only
        // once the dialog is rendered.
        {
            trigger: "button[name='document_layout_save'], .o_error_dialog .o-default-button, .o_dialog .modal-title",
            timeout: 30000,
        },
        {
            isActive: [".o_dialog .modal-header .btn-close"],
            trigger: ".o_dialog .modal-header .btn-close",
            content: markup(_t("Close the warning / document layout dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            // `action_print()` hands the browser a report action: when no
            // document layout is saved yet Odoo first shows the "Configure your
            // document layout" dialog, and once it is closed the report is
            // streamed and the action manager is left EMPTY — there is no
            // form/list/kanban to wait for. Wait for the app navbar, which is
            // always mounted, so the tour can carry on to the next register.
            trigger: ".o_menu_sections, .o_control_panel, .o_action_manager",
        },

        // --- WHT Register ---
        {
            trigger: navSection("Reporting"),
            content: markup(_t("Open the <b>Reporting</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-header:text('Thai Tax Reports')",
            content: markup(_t("Go back to the <b>Thai Tax Reports</b> menu.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: navItem("WHT Register (สมุดภาษีหัก ณ ที่จ่าย)"),
            content: markup(_t(
                "Open <b>WHT Register (สมุดภาษีหัก ณ ที่จ่าย)</b> for withholding tax records."
            )),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "button[name='action_print'], button:contains('Print'), button:contains('Generate')",
            content: markup(_t("Set the period and click <b>Print/Generate</b>.")),
            tooltipPosition: "left",
            run: "click",
        },
        // Printing a register opens a dialog asynchronously: the
        // "Configure your document layout" configurator when no layout has
        // been saved yet, or an "Invalid Operation" warning when the period
        // has no data. Target a *visible* element: the `.o_dialog` wrapper has
        // no box of its own, so a `visible:true` query never matches it (that
        // is why the previous `:has()`-on-`.o_dialog` trigger never fired).
        // A step without run is never blocked by a modal, so it can safely
        // wait for the dialog, and the guarded close below is evaluated only
        // once the dialog is rendered.
        {
            trigger: "button[name='document_layout_save'], .o_error_dialog .o-default-button, .o_dialog .modal-title",
            timeout: 30000,
        },
        {
            isActive: [".o_dialog .modal-header .btn-close"],
            trigger: ".o_dialog .modal-header .btn-close",
            content: markup(_t("Close the warning / document layout dialog.")),
            tooltipPosition: "left",
            run: "click",
        },
        {
            // `action_print()` hands the browser a report action: when no
            // document layout is saved yet Odoo first shows the "Configure your
            // document layout" dialog, and once it is closed the report is
            // streamed and the action manager is left EMPTY — there is no
            // form/list/kanban to wait for. Wait for the app navbar, which is
            // always mounted, so the tour can carry on to the next register.
            trigger: ".o_menu_sections, .o_control_panel, .o_action_manager",
        },

        {
            // Same reason as the steps above: after the last register is
            // printed the action manager is empty, so there is no
            // form/list/kanban left to click. The app navbar is always mounted
            // and gives the final click that closes the tour.
            trigger: ".o_menu_sections, .o_action_manager, .o_control_panel",
            content: markup(_t(
                "Thai Tax Reports complete! Generate <b>VAT Sales Register</b>, " +
                "<b>VAT Purchase Register</b>, and <b>WHT Register</b> for statutory compliance. " +
                "These reports are required for monthly/quarterly tax filings with the Revenue Department."
            )),
            run: "click",
        },
    ],
});
