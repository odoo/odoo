/** @odoo-module **/
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add(
    'industry_fsm_sale_products_compute_catalog_tour',
    {
        url: "/odoo",
        steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
            content: 'Go to the Sale app',
            run: "click",
        },
        {
            trigger: '.o_data_row td:contains("fsm tester")',
            content: 'Open the main_so',
            run: "click",
        },
        {
            trigger: 'button[name="action_view_task"]',
            content: 'Open tasks',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("task 1")',
            content: 'Open the task 1',
            run: "click",
        },
        {
            trigger: 'button[name="action_fsm_view_material"]',
            content: 'Click on the Products stat button',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("Super Product")',
            content: 'Add a Super Product to the main_so',
            run: "click",
        },
        {
            trigger: '.breadcrumb-item :contains("Tasks")',
            content: 'Go back to the tasks',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("task 2")',
            content: 'Open the task 2',
            run: "click",
        },
        {
            trigger: 'button[name="action_fsm_view_material"]',
            content: 'Click on the Products stat button',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("Super Product")',
            content: 'Add a Super Product to the main_so',
            run: "click",
        },
        {
            trigger: '.breadcrumb-item :contains("Tasks")',
            content: 'Go back to the tasks',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("task 3")',
            content: 'Open the task 3',
            run: "click",
        },
        {
            trigger: 'button[name="action_fsm_view_material"]',
            content: 'Click on the Products stat button',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:contains("Super Product")',
            content: 'Add a Super Product to the main_so',
            run: "click",
        },
        // END: Go back to quotations for the last sol of the main_so to update
        {
            trigger: '.breadcrumb-item :contains("Tasks")',
            content: 'Go back to the tasks',
            run: "click",
        },
        {
            trigger: '.breadcrumb-item :contains("Quotations")',
            content: 'Go back to the quotations',
        },
    ]
});
