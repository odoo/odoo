/** @odoo-module **/

<<<<<<< 18.0
    import { registry } from "@web/core/registry";
||||||| b585bb19670172a1a726930e3539c0c23486d89b
    
    import { registry } from "@web/core/registry";
=======
import { registry } from "@web/core/registry";
>>>>>>> 658eec113d2d3453a28019a24fbc93c72d7a0d47

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
    ],
    });

<<<<<<< 18.0

registry.category("web_tour.tours").add('test_multiple_warehouses_filter', {
||||||| b585bb19670172a1a726930e3539c0c23486d89b

registry.category("web_tour.tours").add('test_multiple_warehouses_filter', {
    test: true,
=======
registry.category("web_tour.tours").add("test_context_from_warehouse_filter", {
    test: true,
>>>>>>> 658eec113d2d3453a28019a24fbc93c72d7a0d47
    steps: () => [
        // Add "foo" to the warehouse context key
        {
            trigger: ".o_searchview_input",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            run: "edit foo",
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
            run: "edit warehouse",
        },
        {
            trigger: ".o_menu_item.dropdown-item:contains(Search Warehouse for:) a.o_expand > i",
            run: "click",
        },
        {
            trigger: ".o_menu_item.dropdown-item.o_indent:contains(Warehouse A) a",
            run: "click",
        },
        // Add warehouse B's id to the warehouse context key
        {
            trigger: ".o_searchview_input",
            run: "edit warehouse",
        },
        {
            trigger: ".o_menu_item.dropdown-item:contains(Search Warehouse for:) a.o_expand > i",
            run: "click",
        },
        {
            trigger: ".o_menu_item.dropdown-item.o_indent:contains(Warehouse B) a",
            run: "click",
        },
        {
<<<<<<< 18.0
            trigger: '.o_graph_view',
            content: 'Wait for the Forecast page to load.',
||||||| b585bb19670172a1a726930e3539c0c23486d89b
            trigger: '.o_graph_view',
            content: 'Wait for the Forecast page to load.',
            run: () => {},
=======
            content: "Go to product page",
            trigger: ".o_kanban_record:has(span:contains(Lovely Product))",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            run: () => {
                if (!document.querySelector("button[name=action_product_tmpl_forecast_report]")) {
                    const panelButtons = document.querySelectorAll(
                        ".o_control_panel_actions button"
                    );
                    const moreButton = Array.from(panelButtons).find(
                        (button) => button.textContent.trim() == "More"
                    );
                    moreButton.click();
                }
            },
        },
        {
            trigger: "button[name=action_product_tmpl_forecast_report]",
            run: "click",
        },
        {
            trigger: ".o_graph_view",
>>>>>>> 658eec113d2d3453a28019a24fbc93c72d7a0d47
        },
    ],
});
