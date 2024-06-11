/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('show_expense_receipt_tour', {
    test: true,
    url: '/web',
    steps: () => [
        ...stepUtils.goToAppSteps('hr_expense.menu_hr_expense_root', "Go to the Expenses app"),
        {
            content: "Go to Expense Reports",
            trigger: '.dropdown-item[data-menu-xmlid="hr_expense.menu_hr_expense_report"]',
            position:'bottom',
        },
        {
            content: "Go to a report",
            trigger: '.o_data_row .o_data_cell[name="payment_state"]',
        },
        {
            content: "Click on an expense line 2",
            trigger: '.o_data_row .o_data_cell[data-tooltip="expense_2"]',
        },
        {
            content: "Check attachment",
            trigger: ".o_attachment_preview .o-mail-Attachment-imgContainer .img[src*='test_file_2.png']",
        },
        {
            content: "Click on an expense line 3",
            trigger: '.o_data_row .o_data_cell[data-tooltip="expense_3"]',
        },
        {
            content: "Check attachment",
            trigger: ".o_attachment_preview .o-mail-Attachment-imgContainer .img[src*='test_file_3.png']",
        },
        {
            content: "Click on an expense line 1",
            trigger: '.o_data_row .o_data_cell[data-tooltip="expense_1"]',
        },
        {
            content: "Check attachment",
            trigger: ".o_attachment_preview .o-mail-Attachment-imgContainer .img[src*='test_file_1.png']",
        },
    ],
});
