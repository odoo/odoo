/** @odoo-module **/
import { registry } from "@web/core/registry";


registry.category("web_tour.tours").add('industry_fsm_sale_products_tour', {
    test: true,
    url: "/web",
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
    content: 'Go to industry FSM',
    position: 'bottom',
}, {
    trigger: 'input.o_searchview_input',
    content: 'Search Field Service task',
    run: `text Fsm task`,
}, {
    trigger: '.o_searchview_autocomplete .o_menu_item:contains("Fsm task")',
    content: 'Validate search',
}, {
    trigger: '.o_kanban_record span:contains("Fsm task")',
    content: 'Open task',
}, {
    trigger: 'button[name="action_fsm_view_material"]',
    content: 'Click on the Products stat button',
}, {
    trigger: '.o_control_panel_actions .o_searchview_dropdown_toggler',
    content: 'open search menu',
}, {
    trigger: '.o_search_bar_menu .o_group_by_menu span:contains("Product Type")',
    content: 'group by type',
}, {
    trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Consumable"))) .o_kanban_record:contains("Consommable product ordered")',
    content: 'Add 1 quantity to the Consommable product',
}, {
    trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Consumable"))) .o_kanban_record:contains("1,000.00") button:has(i.fa-plus)',
    content: 'Price is 1000, quantity is 1 and add 1 quantity',
}, {
    trigger: '.o_fsm_product_kanban_view .o_kanban_group:has(.o_kanban_header:has(span:contains("Consumable"))) .o_kanban_record:contains("500.00")',
    content: 'Price is 500',
    isCheck: true,
    id: 'fsm_stock_start'
}]});
