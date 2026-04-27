/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_register_sn_production_quality_check", {
    steps: () => [
        {
            trigger: ".form-check:has(input[name='Lovely Workcenter'])",
            run: "click",
        },
        {
            trigger: "button:contains('Confirm')",
            run: "click",
        },
        {
            content: "Check that we are in the MO view",
            trigger: ".o_mrp_display_records button:contains('Lovely Workcenter')",
            run() {},
        },
        {
            content: "Swap to the WO view of the Lovely Workcenter",
            trigger: "button.btn-light:contains('Lovely Workcenter')",
            run: "click",
        },
        {
            trigger: "button:contains(Instructions)",
            run: "click",
        },
        {
            content: "Register the production",
            trigger: ".modal-content .o_workorder_lot input.o_input",
            run() {},
        },
        // {
        //     content: "Register a new serial number",
        //     trigger: ".modal-content .o_workorder_lot input.o_input",
        //     run: "click",
        // },
        {
            content: "Register a new serial number",
            trigger: ".modal-content .o_workorder_lot input.o_input",
            run: "edit SN0012",
        },
        {
            trigger:
                ".modal-content .o_field_widget[name=lot_id] .dropdown-item:contains(Create and edit)",
            run: "click",
        },
        {
            trigger:
                ".modal-content:has(.modal-header:has(.modal-title:contains(Create Lot/Serial))) .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".modal-header:has(.modal-title:contains(Lovely Production Registering))",
            run: "click",
        },
        {
            content: "Register a new serial number",
            trigger: ".modal-content .o_field_widget[name=qty_done] .o_input",
            run: "edit 1",
        },
        {
            trigger:
                ".modal-content:has(.modal-title:contains(Lovely Production Registering)) button:contains(Validate)",
            run: "click",
        },
        {
            trigger:
                ".o_mrp_display_record:has(.card-header:contains(Lovely Operation)) button:contains(Mark as Done)",
            run() {},
        },
    ],
});
