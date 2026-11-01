import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils, navSection, waitForAction } from "@od19_user_guide_tours/tours/tour_utils";
import { markup } from "@odoo/owl";

/**
 * OD19 Employee Advance Tour
 *
 * Walks the user through an employee salary advance:
 *  1. Open Employee Advances from the Expenses app
 *  2. Create a request (employee, amount, advance account)
 *  3. Follow the approval / payment / clearing workflow
 */
registry.category("web_tour.tours").add("od19_hr_advance_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps(
            "hr_expense.menu_hr_expense_root",
            markup(_t("Let's request an <b>employee advance</b>."))
        ),
        {
            trigger: navSection("Employee Advances"),
            content: markup(_t("Open <b>Employee Advances</b>.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        waitForAction("Employee Advances"),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Each line is an advance with its <b>employee</b>, <b>amount</b> and " +
                "its <b>status</b> (draft → waiting approval → approved → paid → cleared)."
            )),
        },
        {
            trigger: ".o_list_button_add",
            content: markup(_t("Click <b>New</b> to request an advance.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='employee_id'] input",
            content: markup(_t("Pick the <b>employee</b> the advance is granted to (required).")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='date'] .o_input",
            content: markup(_t("Set the <b>request date</b>.")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_field_widget[name='amount'] input",
            content: markup(_t("Enter the <b>amount</b> requested.")),
            tooltipPosition: "bottom",
            run: "edit 5000",
        },
        {
            trigger: ".o_field_widget[name='purpose'] input",
            content: markup(_t("Describe the <b>purpose</b> of the advance.")),
            run: "edit ค่าใช้จ่ายล่วงหน้า (Tour)",
        },
        {
            trigger: ".o_field_widget[name='advance_account_id'] input",
            content: markup(_t(
                "Select the <b>Employee Advance Account</b> used to post the prepayment."
            )),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_form_statusbar",
            content: markup(_t(
                "Follow the workflow with the header buttons: <b>Submit for Approval</b> → " +
                "<b>Pay Advance</b> → <b>Clear</b> once the expenses are justified."
            )),
            tooltipPosition: "bottom",
        },
        ...stepUtils.discardForm(),
        {
            trigger: ".o_list_renderer",
            content: markup(_t(
                "Employee Advance tour complete! Two approvals are required before the " +
                "cash leaves the company."
            )),
            run: "click",
        },
    ],
});
