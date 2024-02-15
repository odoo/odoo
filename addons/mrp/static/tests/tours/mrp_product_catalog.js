/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_mrp_bom_product_catalog', {
    test: true,
    steps: () => [
        { trigger: 'button[name=action_add_from_catalog]' },
        { trigger: 'div.o_kanban_record:nth-child(1)' },
        { trigger: 'div.o_product_added' },
        { trigger: 'button:contains("Back to BoM")' },
        {
            trigger: 'div.o_field_one2many:contains("Component")',
            isCheck: true,
            run() {},
        },
]});
