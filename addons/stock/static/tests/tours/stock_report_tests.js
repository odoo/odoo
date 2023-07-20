/** @odoo-module **/
    
    import { registry } from "@web/core/registry";

    registry.category("web_tour.tours").add('test_stock_route_diagram_report', {
        test: true,
        steps: () => [
    {
        trigger: '.o_kanban_record',
        extra_trigger: '.o_breadcrumb',
    },
    {
        trigger: '.nav-item > a:contains("Inventory")',
    },
    {
        trigger: '.btn[id="stock.view_diagram_button"]',
    },
    {
        trigger: 'iframe .o_report_stock_rule',
        isCheck: true,
    },
    ]});
