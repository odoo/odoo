/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_final_product_quality_check_mrp_barcode", {
    steps: () => [
        {
            trigger: ".o_button_operations",
            run: "click",
        },
        {
            trigger: ".o_kanban_record_title:contains(Manufacturing)",
            run: "click",
        },
        {
            trigger: "button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_barcode_lines",
            run: "scan love724",
        },
        {
            trigger: ".o_barcode_line:contains(Lovely product) .o_add_quantity",
            run: "click",
        },
        {
            content: "check that the qty_producing was set",
            trigger: ".o_barcode_line.o_header_completed",
            run() {},
        },
        {
            trigger: "button:contains(Quality Checks)",
            run: "click",
        },
        {
            trigger: ".modal-content button[name=do_pass]",
            run: "click",
        },
        {
            trigger: ".o_validate_page",
            run: "click",
        },
        {
            trigger: ".o_notification_bar.bg-success",
            run() {},
        },
    ],
});
