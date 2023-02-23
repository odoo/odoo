odoo.define('stock.reports.setup.tour', function (require) {
    "use strict";

    const { registry } = require("@web/core/registry");

    registry.category("web_tour.tours").add('test_stock_route_diagram_report', {
        test: true,
        steps: [
    {
        trigger: '.o_kanban_record',
        extra_trigger:'.breadcrumb',
    },
    {
        trigger: '.nav-item > a:contains("Inventory")',
    },
    {
        trigger: '.btn[id="stock.view_diagram_button"]',
    },
    {
        trigger: 'iframe .o_report_stock_rule',
    },
    ]});
});
