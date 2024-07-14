/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_multiple_worksheet_checks', {
    test: true,
    steps: () => [
        {
            content: 'Open Quality check worksheets',
            trigger: 'button[name="check_quality"]',
        },
        {
            content: 'Save the worksheet as failed',
            extra_trigger: '.modal-title:contains("Office Chair")',
            trigger: '.o_form_button_save',
        },
        {
            content: 'Enter failed qty',
            extra_trigger: '.modal-title:contains("Check Failed for Office Chair")',
            trigger: 'div[name="qty_failed"] .o_input',
            run: 'text 1.0',
        },
        {
            content: 'Choose fail location',
            trigger: '.o_selection_badge',
        },
        {
            content: 'Confirm failed check',
            trigger: 'button[name="confirm_fail"]',
        },
        {
            content: 'Mark the next worksheet as passed',
            extra_trigger: '.modal-title:contains("Test Product")',
            trigger: 'div[name="x_passed"] .form-check-input',
        },
        {
            content: 'Save the worksheet',
            trigger: '.o_form_button_save',
        },
        {
            content: 'Quality checks color is danger since one failed',
            trigger: 'button[name="action_open_quality_check_picking"] .text-danger',
            run: () => {},
        }
    ]
});
