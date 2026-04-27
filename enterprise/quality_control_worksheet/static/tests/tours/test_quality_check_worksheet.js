/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_multiple_worksheet_checks", {
    steps: () => [
        {
            content: "Open Quality check worksheets",
            trigger: 'button[name="check_quality"]',
            run: "click",
        },
        {
            trigger: '.modal:not(.o_inactive_modal) .modal-title:contains("Office Chair")',
        },
        {
            content: "Save the worksheet as failed",
            trigger:
                ".modal:not(.o_inactive_modal):contains(Office Chair) .o_form_button_save:contains(validate)",
            run: "click",
        },
        {
            trigger:
                '.modal:not(.o_inactive_modal) .modal-title:contains("Check Failed for Office Chair")',
        },
        {
            content: "Enter failed qty",
            trigger:
                '.modal:not(.o_inactive_modal):contains(Check Failed for Office Chair) div[name="qty_failed"] .o_input',
            run: "edit 1.0",
        },
        {
            content: "Choose fail location",
            trigger: ".modal:not(.o_inactive_modal) .o_selection_badge",
            run: "click",
        },
        {
            content: "Confirm failed check",
            trigger: '.modal:not(.o_inactive_modal) button[name="confirm_fail"]',
            run: "click",
        },
        {
            trigger: '.modal:not(.o_inactive_modal) .modal-title:contains("Test Product")',
        },
        {
            content: "Mark the next worksheet as passed",
            trigger: '.modal:not(.o_inactive_modal):contains(Test Product) div[name="x_passed"] .form-check-input',
            run: "click",
        },
        {
            content: "Save the worksheet",
            trigger: ".modal:not(.o_inactive_modal) .o_form_button_save:contains(validate)",
            run: "click",
        },
        {
            content: "Quality checks color is danger since one failed",
            trigger: 'button[name="action_open_quality_check_picking"] .text-danger',
        },
    ],
});
