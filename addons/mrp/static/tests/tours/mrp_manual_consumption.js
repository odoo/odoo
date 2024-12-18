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
            run: 'text 16.0'
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
            run: 'text 8.0',
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

registry.category("web_tour.tours").add('test_mrp_manual_consumption_03', {
    test: true,
    steps: () => [
        {
            trigger: "button:has(input[name='Nuclear Workcenter'])",
            run: "click",
        },
        {
            extra_trigger: "button.active:has(input[name='Nuclear Workcenter'])",
            trigger: "button:contains('Confirm')",
            run: "click",
        },
        {
            trigger: "button.btn-light:contains('Nuclear Workcenter')",
            run: 'click',
        },
        {
            extra_trigger: ".o_control_panel_actions button.active:contains('Nuclear Workcenter')",
            trigger: ".o_finished_product span:contains('Finish')",
            run: 'click',
        },
        {
            trigger: ".o_mrp_record_line:not(.text-muted) span:contains('Component')",
        },
        {
            trigger: ".o_finished_product span:contains('Finish')",
            run: 'click',
        },
]});
