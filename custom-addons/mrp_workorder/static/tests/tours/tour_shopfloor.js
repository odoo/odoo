/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TourError } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('test_shop_floor', {test: true, steps: () => [
    {
        content: 'Select the workcenter the first time we enter in shopfloor',
        trigger: 'button:has(input[name="Savannah"])'
    },
    {
        content: 'Select the second workcenter',
        extra_trigger: 'button.active:has(input[name="Savannah"])',
        trigger: 'button:has(input[name="Jungle"])'
    },
    {
        extra_trigger: 'button.active:has(input[name="Jungle"])',
        trigger: 'footer.modal-footer button.btn-primary'
    },
    {
        content: 'Open the employee panel',
        extra_trigger: '.o_control_panel_actions button:contains("Savannah")',
        trigger: 'button[name="employeePanelButton"]'
    },
    {
        content: 'Add operator button',
        trigger: 'button:contains("Operator")'
    },
    {
        content: 'Select the Marc Demo employee',
        trigger: '.modal-body .popup .selection div:contains("Marc Demo")'
    },
    {
        content: 'Go to workcenter Savannah from MO card',
        extra_trigger: '.o_mrp_employees_panel li.o_admin_user:contains(Marc Demo)',
        trigger: '.o_mrp_record_line button span:contains("Savannah")'
    },
    {
        content: 'Start the workorder on header click',
        extra_trigger: '.o_control_panel_actions button.active:contains("Savannah")',
        trigger: '.o_finished_product span:contains("Giraffe")'
    },
    {
        content: 'Register production check',
        extra_trigger: '.o_mrp_display_record.o_active',
        trigger: '.o_mrp_record_line .btn.fa-plus'
    },
    {
        content: 'Instruction check via form',
        extra_trigger: 'span.o_qc_lot',
        trigger: '.o_mrp_record_line span:contains("Instructions")'
    },
    { trigger: 'button[barcode_trigger="Next"]' },
    {
        content: 'Component not tracked registration and continue production',
        extra_trigger: '.modal-title:contains("Register legs")',
        trigger: 'button[barcode_trigger="continue"]'
    },
    {
        content: 'Add 2 units',
        extra_trigger: '.o_field_widget[name="qty_done"] input:propValue("0.00")',
        trigger: '.o_field_widget[name="qty_done"] input',
        run: 'text 2',
    },
    {
        extra_trigger: '.o_field_widget[name="qty_done"] input:propValue("2.00")',
        trigger: 'button[barcode_trigger="Next"]'
    },
    {
        extra_trigger: '.modal-title:contains("Release")',
        trigger: '.modal-header .btn-close'
    },
    {
        content: 'Fast check last instruction step',
        extra_trigger: '.o_web_client:not(.modal-open)',
        trigger: '.o_mrp_record_line .fa-square-o',
    },
    {
        content: 'Close first operation',
        extra_trigger: '.o_mrp_record_line:contains("Release") button.text-success',
        trigger: '.card-footer button[barcode_trigger="cloWO"]',
    },
    {
        content: 'Switch to second workcenter for next operation',
        extra_trigger: '.o_nocontent_help',
        trigger: '.o_control_panel_actions button:contains("Jungle")',
    },
    {
        content: 'Open the WO setting menu again',
        trigger: '.o_mrp_display_record:contains("Release") .card-footer button.fa-ellipsis-v',
    },
    {
        content: 'Add an operation button',
        trigger: 'button[name="addComponent"]',
    },
    {
        content: 'Add Color',
        trigger: '.o_field_widget[name=product_id] input',
        run: 'text color'
    },
    { trigger: '.ui-menu-item > a:contains("Color")' },
    {
        extra_trigger: 'div.o_dialog input#product_id_0:propValue("Color")',
        trigger: 'button[name=add_product]',
    },
    {
        extra_trigger: 'body:not(.modal-open)',
        trigger: '.o_mrp_record_line .btn-secondary:contains("2")'
    },
    { trigger: 'button[barcode_trigger=cloWO]' },
    { trigger: 'button[barcode_trigger=cloMO]' },
    {
        content: 'Leave shopfloor',
        extra_trigger: '.o_nocontent_help',
        trigger: '.o_home_menu .fa-sign-out',
    },
    { trigger: '.o_apps', isCheck: true }
]})

registry.category("web_tour.tours").add('test_generate_serials_in_shopfloor', {test: true, steps: () => [
    {
        content: 'Make sure workcenter is available',
        trigger: 'button:has(input[name="Assembly Line"])',
    },
    {
        content: 'Confirm workcenter',
        extra_trigger: 'button.active:has(input[name="Assembly Line"])',
        trigger: 'button:contains("Confirm")',
    },
    {
        content: 'Select workcenter',
        trigger: 'button.btn-light:contains("Assembly Line")',
    },
    {
        content: 'Open the wizard',
        trigger: '.o_mrp_record_line .text-truncate:contains("Register byprod")',
    },
    {
        content: 'Open the serials generation wizard',
        trigger: '.o_widget_generate_serials button',
    },
    {
        content: 'Input a serial',
        trigger: '#next_serial_0',
        run: 'text 00001',
    },
    {
        content: 'Generate the serials',
        trigger: 'button.btn-primary:contains("Generate")',
    },
    {
        content: 'Save and close the wizard',
        trigger: '.o_form_button_save:contains("Save")',
    },
    {
        content: 'Set production as done',
        trigger: 'button.btn-primary:contains("Mark as Done")',
    },
    {
        content: 'Close production',
        trigger: 'button.btn-primary:contains("Close Production")',
        isCheck: true,
    },
]})

registry.category("web_tour.tours").add('test_canceled_wo', {
    test: true, steps: () => [
        {
            content: 'Make sure workcenter is available',
            trigger: 'button:has(input[name="Assembly Line"])',
        },
        {
            content: 'Confirm workcenter',
            extra_trigger: 'button.active:has(input[name="Assembly Line"])',
            trigger: 'button:contains("Confirm")',
        },
        {
            content: 'Check MO',
            trigger: 'button.btn-light:contains("Assembly Line")',
            isCheck: true,
            run: () => {
                if (document.querySelectorAll("ul button:not(.btn-secondary)").length > 1)
                    throw new TourError("Multiple Workorders");
            }
        },
    ]
})
