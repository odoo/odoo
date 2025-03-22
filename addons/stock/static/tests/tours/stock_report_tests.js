odoo.define('stock.reports.setup.tour', function (require) {
    "use strict";

    const tour = require('web_tour.tour');

    tour.register('test_stock_route_diagram_report', {
        test: true,
    }, [
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
    ]);

    tour.register("test_context_from_warehouse_filter", { test: true }, [
        // Add "foo" to the warehouse context key
        {
            trigger: ".o_searchview_input",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            run: "text foo",
        },
        {
            trigger: ".o_menu_item.dropdown-item:contains(Warehouse):contains(foo)",
            run: "click",
        },
        // Add warehouse A's id to the warehouse context key
        {
            trigger: ".o_searchview_input",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            run: "text warehouse",
        },
        {
            trigger: ".o_menu_item.dropdown-item:contains(Warehouse) a.o_expand > i",
            run: "click",
        },
        {
            trigger: ".o_menu_item.dropdown-item.o_indent:contains(Warehouse A) a",
            run: "click",
        },
        // Add warehouse B's id to the warehouse context key
        {
            trigger: ".o_searchview_input",
            run: "text warehouse",
        },
        {
            trigger: ".o_menu_item.dropdown-item:contains(Warehouse) a.o_expand > i",
            run: "click",
        },
        {
            trigger: ".o_menu_item.dropdown-item.o_indent:contains(Warehouse B) a",
            run: "click",
        },
        {
            content: "Go to product page",
            trigger: ".oe_kanban_card:has(.o_kanban_record_title span:contains(Lovely Product))",
            run: "click",
        },
        {
            trigger: "button[name=action_product_tmpl_forecast_report]",
            run: "click",
        },
        {
            trigger: ".o_graph_view",
            isCheck: true,
        },
    ]);
});
