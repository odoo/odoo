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


registry.category("web_tour.tours").add('test_multiple_warehouses_filter', {
    test: true,
    steps: () => [
        // Add (Warehouse A or Warehouse B) to the filter
        {
            content: "click search",
            trigger: '.o_searchview_input',
            run: 'click',
        },
        {
            trigger: '.o_searchview_input',
            run: 'text warehouse',
        },
        {
            trigger: '.o_menu_item.dropdown-item:contains("Warehouse") a.o_expand > i',
            run: 'click',
        },
        {
            trigger: '.o_menu_item.dropdown-item.o_indent:contains("Warehouse A") a',
            run: 'click',
        },
        {
            trigger: '.o_searchview_input',
            run: 'text warehouse',
        },
        {
            trigger: '.o_menu_item.dropdown-item:contains("Warehouse") a.o_expand > i',
            run: 'click',
        },
        {
            trigger: '.o_menu_item.dropdown-item.o_indent:contains("Warehouse B") a',
            run: 'click',
        },
        // Go to product page
        {
            trigger: '.oe_kanban_card:has(.o_kanban_record_title span:contains("Product A"))',
            run: 'click',
        },
        // Forecast page should load correctly
        {
            trigger: '.dropdown-toggle.o_button_more:contains("More")',
            run: 'click',
        },
        {
            trigger: 'button[name="action_product_tmpl_forecast_report"]',
            run: 'click',
        },
        {
            trigger: '.o_graph_view',
            content: 'Wait for the Forecast page to load.',
            extra_trigger: '.o_graph_view',
            run: () => {},
        },
    ],
});
