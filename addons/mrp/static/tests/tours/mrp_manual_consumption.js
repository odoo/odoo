/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from '@web_tour/tour_service/tour_utils';

registry.category("web_tour.tours").add('test_mrp_manual_consumption', {
    test: true,
    steps: () => [
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last:contains("5.00")',
            run: () => {},
        },
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last',
            run: 'click',
        },
        {
            trigger: 'div[name="quantity"] input',
            run: 'text 6.0'
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
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last:contains("6.00")',
            run: () => {},
        },
        {
            trigger: 'button[name=button_mark_done]',
            run: 'click',
        },
        {
            trigger: 'button[name=action_confirm]',
            extra_trigger: '.o_technical_modal',
            run: 'click',
        },
        {
            trigger: 'button[name=action_backorder]',
            run: 'click',
        },
        {
            trigger: "input[id='qty_producing_0']",
            run: 'text 2.0',
        },
        {
            content: "Click Pager",
            trigger: ".o_pager_value:first()",
        },
        {
            trigger: 'div[name=move_raw_ids] td[name="quantity"]:last:contains("2.00")',
            run: () => {},
        },
        {
            trigger: 'button[name=button_mark_done]',
            run: 'click',
        },
        {
            trigger: 'button[name=action_confirm]',
            extra_trigger: '.o_technical_modal',
            run: 'click',
        },
        ...stepUtils.saveForm(),
]});

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
