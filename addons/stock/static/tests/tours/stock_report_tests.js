/** @odoo-module **/
    
    import { registry } from "@web/core/registry";

    registry.category("web_tour.tours").add('test_stock_route_diagram_report', {
        test: true,
        steps: () => [
        {
            trigger: ".o_breadcrumb",
        },
    {
        trigger: '.o_kanban_record',
        run: "click",
    },
    {
        trigger: '.nav-item > a:contains("Inventory")',
        run: "click",
    },
    {
        trigger: '.btn[id="stock.view_diagram_button"]',
        run: "click",
    },
    {
        trigger: ':iframe .o_report_stock_rule',
    },
    ]});
