/** @odoo-module **/
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add(
    'industry_fsm_sale_products_compute_catalog_tour',
    {
        test: true,
        url: "/web",
        steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="sale.sale_menu_root"]',
            content: 'Go to the Sale app',
        },
        {
            trigger: '.o_data_row td:contains("fsm tester")',
            content: 'Open the main_so',
        },
        {
            trigger: 'button[name="action_view_task"]',
            content: 'Open tasks',
        },
        {
            trigger: '.o_kanban_record_top .o_kanban_record_headings:has(.o_kanban_record_title:has(span:contains("task 1")))',
            content: 'Open the task 1',
        },
        {
            trigger: 'button[name="action_fsm_view_material"]',
            content: 'Click on the Products stat button',
        },
        {
            trigger: '.o_kanban_record_top .o_kanban_record_title:has(span:contains("Super Product"))',
            content: 'Add a Super Product to the main_so',
        },
        {
            trigger: '.breadcrumb-item :contains("Tasks")',
            content: 'Go back to the tasks'
        },
        {
            trigger: '.o_kanban_record_top .o_kanban_record_headings:has(.o_kanban_record_title:has(span:contains("task 2")))',
            content: 'Open the task 2',
        },
        {
            trigger: 'button[name="action_fsm_view_material"]',
            content: 'Click on the Products stat button',
        },
        {
            trigger: '.o_kanban_record_top .o_kanban_record_title:has(span:contains("Super Product"))',
            content: 'Add a Super Product to the main_so',
        },
        {
            trigger: '.breadcrumb-item :contains("Tasks")',
            content: 'Go back to the tasks'
        },
        {
            trigger: '.o_kanban_record_top .o_kanban_record_headings:has(.o_kanban_record_title:has(span:contains("task 3")))',
            content: 'Open the task 3',
        },
        {
            trigger: 'button[name="action_fsm_view_material"]',
            content: 'Click on the Products stat button',
        },
        {
            trigger: '.o_kanban_record_top .o_kanban_record_title:has(span:contains("Super Product"))',
            content: 'Add a Super Product to the main_so',
        },
        // END: Go back to quotations for the last sol of the main_so to update
        {
            trigger: '.breadcrumb-item :contains("Tasks")',
            content: 'Go back to the tasks',
        },
        {
            trigger: '.breadcrumb-item :contains("Quotations")',
            content: 'Go back to the quotations',
            isCheck: true,
        },
    ]
});
