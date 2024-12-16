/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("hr_expense_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            isActive: ["community"],
            trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
            content: markup(
                _t("<b>Wasting time recording your receipts?</b> Let’s try a better way.")
            ),
            tooltipPosition: "right",
            run: "click",
        },
        {
            isActive: ["enterprise"],
            trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
            content: markup(
                _t("<b>Wasting time recording your receipts?</b> Let’s try a better way.")
            ),
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_button_upload_expense",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_list_button_add",
            content: _t("It all begins here - let's go!"),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: ".o_button_upload_expense",
        },
        {
            isActive: ["mobile"],
            trigger: ".o-kanban-button-new",
            content: _t("It all begins here - let's go!"),
            run: "click",
        },
        {
            trigger: '.o_hr_expense_form_view_view .o_field_widget[name="name"] input',
            content: _t("Enter a name of your expense"),
            run: "edit name_of_expense",
        },
        {
            trigger: '.o_hr_expense_form_view_view .o_field_widget[name="product_id"] input',
            content: _t("Enter a category of your expense."),
            run: "edit cat1",
        },
        {
            trigger:
                '.o_hr_expense_form_view_view .o_field_widget[name="total_amount_currency"] input',
            content: _t("Enter the amount of your expense."),
            run: "edit 12345678",
        },
        {
            trigger:
                ".o_hr_expense_form_view_view .o_control_panel_breadcrumbs .o_form_button_save",
            content: markup(
                _t(
                    "Ready? You can save it manually or discard modifications from here. You don't <em>need to save</em> - Odoo will save eveyrthing for you when you navigate."
                )
            ),
            run: "click",
        },
        ...stepUtils.statusbarButtonsSteps(
            _t("Attach Receipt"),
            _t("Attach a receipt - usually an image or a PDF file.")
        ),
        {
            trigger: "body",
            isActive: ["auto"],
            run: "press Escape",
        },
        ...stepUtils.statusbarButtonsSteps(
            _t("Create Report"),
            _t("Create a report to submit one or more expenses to your manager.")
        ),
        ...stepUtils.statusbarButtonsSteps(
            _t("Submit to Manager"),
            markup(
                _t(
                    "Once your <b>Expense Report</b> is ready, you can submit it to your manager and wait for approval."
                )
            )
        ),
        {
            isActive: ["mobile"],
            trigger: ".o_back_button",
            content: _t("Use the breadcrumbs to go back to the list of expenses."),
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: ".breadcrumb > li.breadcrumb-item:first",
            content: _t("Let's go back to your expenses."),
            run: "click",
        },
        {
            trigger: ".o_expense_container",
            content: _t("The status of all your current expenses is visible from here."),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: ".o_mobile_menu_toggle",
            content: _t("Open bugger menu."),
            run: "click",
        },
        {
            trigger: ".o_main_navbar",
        },
        {
            trigger: "[data-menu-xmlid='hr_expense.menu_hr_expense_report']",
            content: _t("Let's check out where you can manage all your employees expenses"),
            run: "click",
        },
        {
            isActive: ["desktop"],
            trigger: ".o_list_renderer tbody tr[data-id]",
            content: _t("Managers can inspect all expenses from here."),
            run: "click",
        },
        {
            isActive: ["mobile"],
            trigger: ".o_kanban_renderer .oe_kanban_card",
            content: _t("Managers can inspect all expenses from here."),
            run: "click",
        },
        {
            content: _t("Click on first expense."),
            trigger: ".hr_expense tbody tr:first td:eq(1)",
            run: "click",
        },
        ...stepUtils.statusbarButtonsSteps(
            _t("Approve"),
            _t(
                "Managers can approve the report here, then an accountant can post the accounting entries."
            )
        ),
    ],
});
