/** @odoo-module **/
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add('industry_fsm_sale_products_tour', {
    url: "/odoo",
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
    content: 'Go to industry FSM',
    tooltipPosition: 'bottom',
    run: "click",
}, {
    trigger: 'input.o_searchview_input',
    content: 'Search Field Service task',
    run: `fill Fsm task`,
}, {
    trigger: '.o_searchview_autocomplete .o_menu_item:contains("Fsm task")',
    content: 'Validate search',
    run: "click",
}, {
    trigger: '.o_kanban_record span:contains("Fsm task")',
    content: 'Open task',
    run: "click",
}, {
    trigger: 'button[name="action_fsm_view_material"]',
    content: 'Click on the Products stat button',
    run: "click",
}, {
    trigger: '.o_control_panel_actions .o_searchview_dropdown_toggler',
    content: 'open search menu',
    run: "click",
}, {
    trigger: '.o_search_bar_menu .o_group_by_menu span:contains("Product Type")',
    content: 'group by type',
    run: "click",
}, {
    trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Goods"))) .o_kanban_record:contains("Consommable product ordered")',
    content: 'Add 1 quantity to the Consommable product',
    run: "click",
}, {
    trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Goods"))) .o_kanban_record:contains("1,000.00") button:has(i.fa-plus)',
    content: 'Price is 1000, quantity is 1 and add 1 quantity',
    run: "click",
}, {
    trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Goods"))) .o_kanban_record:contains("500.00")',
    content: 'Price is 500',
    id: 'fsm_stock_start'
}]});

registry.category("web_tour.tours").add("test_industry_fsm_sale_add_product_on_invoice_tour", {
    url: "/odoo/field-service",
    steps: () => [
        {
            trigger: "input.o_searchview_input",
            content: "Search Field Service task",
            run: `edit Fsm task`,
        },
        {
            trigger: '.o_searchview_autocomplete .o_menu_item:contains("Fsm task")',
            content: "Validate search",
            run: "click",
        },
        {
            trigger: '.o_kanban_record span:contains("Fsm task")',
            content: "Open task",
            run: "click",
        },
        {
            trigger: ".o_form_sheet",
            run: function (action) {
                const moreButton = document.querySelector(".o_button_more");
                if (moreButton) {
                    action.click(moreButton);
                }
            },
        },
        {
            trigger: "[name=action_view_invoices]",
            content: "Go to the invoices",
            run: "click",
        },
        {
            trigger: "a:contains('Add a line')",
            run: "click",
        },
        {
            trigger: "[name='product_id'] input",
            run: "edit sale product",
        },
        {
            trigger: '.dropdown-item:contains(Sale Product):not(:contains(create "sale product"))',
            run: "click",
        },

        {
            trigger: "[name=action_post]",
            run: "click",
        },
        {
            trigger: '.o_field_widget:contains("INV/")',
        },
    ],
});
