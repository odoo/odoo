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
    ],
    });

registry.category("web_tour.tours").add("test_context_from_warehouse_filter", {
    test: true,
    steps: () => [
        // Add "foo" to the warehouse context key
        {
            trigger: ".o_searchview_input",
            run: "click",
        },
        {
<<<<<<< saas-17.4
            trigger: '.o_searchview_input',
            run: 'edit warehouse',
||||||| 562e053de5b0265d255df49d6f20140247d76740
            trigger: '.o_searchview_input',
            run: 'text warehouse',
=======
            trigger: ".o_searchview_input",
            run: "text foo",
>>>>>>> f2b65aa9a8ca39dc5b12a2c9e6681a05a23aa131
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
<<<<<<< saas-17.4
            trigger: '.o_searchview_input',
            run: 'edit warehouse',
||||||| 562e053de5b0265d255df49d6f20140247d76740
            trigger: '.o_searchview_input',
            run: 'text warehouse',
=======
            trigger: ".o_menu_item.dropdown-item:contains(Search Warehouse for:) a.o_expand > i",
            run: "click",
>>>>>>> f2b65aa9a8ca39dc5b12a2c9e6681a05a23aa131
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
<<<<<<< saas-17.4
            trigger: '.o_menu_item.dropdown-item.o_indent:contains("Warehouse B") a',
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
||||||| 562e053de5b0265d255df49d6f20140247d76740
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
=======
            trigger: ".o_menu_item.dropdown-item:contains(Search Warehouse for:) a.o_expand > i",
            run: "click",
>>>>>>> f2b65aa9a8ca39dc5b12a2c9e6681a05a23aa131
        },
        {
            trigger: ".o_menu_item.dropdown-item.o_indent:contains(Warehouse B) a",
            run: "click",
        },
        {
<<<<<<< saas-17.4
            trigger: '.o_graph_view',
            content: 'Wait for the Forecast page to load.',
||||||| 562e053de5b0265d255df49d6f20140247d76740
            trigger: '.o_graph_view',
            content: 'Wait for the Forecast page to load.',
            extra_trigger: '.o_graph_view',
=======
            content: "Go to product page",
            trigger: ".oe_kanban_card:has(.o_kanban_record_title span:contains(Lovely Product))",
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
>>>>>>> f2b65aa9a8ca39dc5b12a2c9e6681a05a23aa131
            run: () => {},
        },
    ],
});
