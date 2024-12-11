    import { registry } from "@web/core/registry";

    registry.category("web_tour.tours").add('test_stock_route_diagram_report', {
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


registry.category("web_tour.tours").add('test_multiple_warehouses_filter', {
    steps: () => [
        // Add (Warehouse A or Warehouse B) to the filter
        {
            content: "click search",
            trigger: '.o_searchview_input',
            run: 'click',
        },
        {
            trigger: '.o_searchview_input',
            run: 'edit warehouse',
        },
        {
            trigger: '.o-dropdown-item:contains("Search Warehouse for:") a.o_expand > i',
            run: 'click',
        },
        {
            trigger: '.o-dropdown-item.o_indent:contains("Warehouse A") a',
            run: 'click',
        },
        {
            trigger: '.o_searchview_input',
            run: 'edit warehouse',
        },
        {
            trigger: '.o-dropdown-item:contains("Search Warehouse for:") a.o_expand > i',
            run: 'click',
        },
        {
            trigger: '.o-dropdown-item.o_indent:contains("Warehouse B") a',
            run: 'click',
        },
        // Go to product page
        {
            trigger: '.o_kanban_record:has(span:contains("AAProduct"))',
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
        },
    ],
});
