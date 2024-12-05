import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("show_expense_receipt_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("hr_expense.menu_hr_expense_root", "Go to the Expenses app"),
        {
            content: "Go to Expenses",
            trigger: '.dropdown-item[data-menu-xmlid="hr_expense.menu_hr_expense_all_expenses"]',
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            content: "Go to an expense",
            trigger: '.o_data_row .o_data_cell[name="payment_state"]',
            run: "click",
        },
        {
            content: "Check attachment",
            trigger:
                ".o_attachment_preview .o-mail-Attachment-imgContainer .img[src*='test_file_2.png']",
            run: "click",
        },
    ],
});
