/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from '@web_tour/tour_service/tour_utils';
registry.category("web_tour.tours").add('test_mrp_manual_consumption_02', {
    test: true,
    steps: () => [
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last:contains("0.00")',
            run: () => {},
        },
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last',
            run: 'click',
        },
        {
            trigger: 'div[name="quantity"] input',
            run: "edit 16.0 && click body",
        },
        {
            trigger: 'div[name="picked"] input',
            run: 'click',
        },
        {
            content: "Click Pager",
            trigger: ".o_pager_value:first()",
        },
        {
            trigger: "input[id='qty_producing_0']",
            run: "edit 8.0 && click body",
        },
        {
            content: "Click Pager",
            trigger: ".o_pager_value:first()",
        },
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last:contains("16.00")',
            run: () => {},
        },
        ...stepUtils.saveForm(),
]});
