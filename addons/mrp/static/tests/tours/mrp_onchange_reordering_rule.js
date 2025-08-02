/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('mrp_reordering_rule_onchange_tour', {
    steps: () => [
        {
            trigger: 'button[data-menu-xmlid="mrp.menu_mrp_bom"]',
            content: 'Open the Products dropdown menu.',
            run: 'click',
        },
        {
            trigger: '.dropdown-item[data-menu-xmlid="mrp.menu_mrp_product_form"]',
            content: 'Click on the Products menu item.',
            run: 'click',
        },
        {
            trigger: '.o_kanban_record:first',
            content: 'Open the first product in the list (marked as favorite).',
            run: 'click',
        },
        {
            trigger: '.o_button_more',
            content: 'Click the "More" dropdown button.',
            run: 'click',
        },
        {
            trigger: 'button[name="action_view_orderpoints"]',
            content: 'Click on the Reordering Rules button.',
            run: 'click',
        },
        {
            trigger: '.o_data_row td[name="product_min_qty"]',
            content: 'Click on the Min Quantity cell to edit it.',
            run: 'click',
        },
        {
            trigger: '.o_data_row td[name="product_min_qty"]',
            content: 'Change the minimum quantity of the first reordering rule.',
            run: 'edit 15', 
        },
        {
            trigger: '.o_data_row td[name="product_max_qty"]',
            content: 'Click on the Max Quantity cell to trigger compute methods.',
            run: 'click',
        },
    ]
});
