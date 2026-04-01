import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_stock_route_diagram_report", {
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

registry.category("web_tour.tours").add("test_context_from_warehouse_filter", {
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
            trigger: ".o-dropdown-item:contains(Warehouse):contains(foo)",
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
            trigger: ".o-dropdown-item:contains(Search Warehouse for:) a.o_expand > i",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item.o_indent:contains(Warehouse A) a",
            run: "click",
        },
        // Add warehouse B's id to the warehouse context key
        {
            trigger: ".o_searchview_input",
            run: "edit warehouse",
        },
        {
            trigger: ".o-dropdown-item:contains(Search Warehouse for:) a.o_expand > i",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item.o_indent:contains(Warehouse B) a",
            run: "click",
        },
        {
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
        },
    ],
});

registry.category("web_tour.tours").add("test_forecast_replenishment", {
    steps: () => [
        {
            trigger: ".o_kanban_record:contains(Lovely product)",
            run: "click",
        },
        {
            trigger: "button[name=action_product_tmpl_forecast_report]",
            run: "click",
        },
        {
            trigger: "button.o_forecasted_replenish_btn",
            run: "click",
        },
        {
            trigger: ".modal-dialog .btn-close",
            run: "click",
        },
        {
            trigger: ".o_web_client:not(:has(.modal-dialog))",
        },
        {
            trigger: "button.o_forecasted_replenish_btn",
            run: "click",
        },
        {
            trigger: "button[name=launch_replenishment]",
            run: "click",
        },
        {
            trigger: ".o_web_client:not(:has(.modal-dialog))",
        },
        {
            trigger:
                ".o_notification:contains(The following replenishment order have been generated)",
        },
    ],
});
