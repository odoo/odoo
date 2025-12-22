/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_mrp_bom_product_catalog', {
    steps: () => [
        {
            trigger: 'button[name=action_add_from_catalog]',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:nth-child(1)',
            run: "click",
        },
        {
            trigger: '.o_product_added',
            run: "click",
        },
        {
            trigger: 'button:contains("Back to BoM")',
            run: "click",
        },
        {
            trigger: 'div.o_field_one2many:contains("Component")',
        },
]});

registry.category("web_tour.tours").add('test_mrp_production_product_catalog', {
    steps: () => [
        {
            trigger: 'button[name=action_add_from_catalog_raw]',
            run: "click",
        },
        {
            trigger: '.o_kanban_record:nth-child(1)',
            run: "click",
        },
        {
            trigger: '.o_product_added',
            run: "click",
        },
        {
            trigger: 'button:contains("Back to Production")',
            run: "click",
        },
        {
            trigger: 'div.o_field_widget:contains("WH/MO/")',
        },
]});
