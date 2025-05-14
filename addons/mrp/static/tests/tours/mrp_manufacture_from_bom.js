/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_manufacture_from_bom", {
    steps: () => [
        {
            trigger: '[name="product_tmpl_id"]',
            run: "click",
        },
        {
            trigger: '.o_stat_text:contains("BoM Overview")',
            run: "click",
        },
        {
            trigger: 'button.btn-primary:contains("Manufacture")',
            run: "click",
        },
        {
            trigger: 'button[aria-checked="true"]:contains("Draft")',
        },
    ],
});

registry.category("web_tour.tours").add('test_mrp_lot_generation_quantity_check', {
    steps: () => [
        {
            content: 'Make sure workcenter is available',
            trigger: 'input[name="Test Workcenter"]',
            run: "click",
        },
        {
            content: 'Verify that the workcenter is selected',
            trigger: 'input:checked[name="Test Workcenter"]',
        },
        {
            content: 'Confirm the selected workcenter',
            trigger: 'button:contains("Confirm")',
            run: "click",
        },
        {
            content: "open the operations wizard",
            trigger: '.o_mrp_record_line .text-truncate:contains("Tracked by Lots")',
            run: "click",
        },
        {
            content: 'Click on Generate Serials/Lots',
            trigger: '.o_widget_generate_serials button',
            run: "click",
        },
        {
            content: 'Input a serial',
            trigger: '#next_serial_0',
            run: "edit 00001",
        },
        {
            content: 'Generate the serial numbers',
            trigger: 'button.btn-primary:contains("Generate")',
            run: "click",
        },
    ]
})
