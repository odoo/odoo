/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('industry_fsm_sale_quantity_products_tour', {
    test: true,
    url: "/web",
    steps: () => [{
    trigger: '.o_app[data-menu-xmlid="industry_fsm.fsm_menu_root"]',
    content: 'Go to industry FSM',
    position: 'bottom',
}, {
    trigger: '.o_kanban_record span:contains("Fsm task")',
    content: 'Open task',
}, {
    trigger: 'button[name="action_fsm_view_material"]',
    content: 'Open products kanban view',
}, {
    trigger: '.o_kanban_record:nth-child(2) .o-dropdown .dropdown-toggle',
    content: 'Click the dropdown toggle in the second kanban-box',
}, {
    trigger: '.o_kanban_record:nth-child(2) .o_dropdown_kanban .dropdown-item:contains("Edit")',
    content: 'Click the "Edit" dropdown item in the second kanban-box',
}, {
    trigger: '.breadcrumb-item.o_back_button:nth-of-type(3)',
    content: 'Back to the list of products',
    position: 'bottom',
}, {
    trigger: '.o_kanban_record:nth-child(2) .o_product_catalog_buttons .btn-secondary:contains("Add")',
    content: 'Assert that the Add button does not convert to Remove',
    isCheck: true,
}]});
