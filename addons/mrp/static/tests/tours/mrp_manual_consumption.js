/** @odoo-module **/

import tour from 'web_tour.tour';


tour.register('test_mrp_manual_consumption', {test: true}, [
    {
        trigger: 'div[name=move_raw_ids] td[name="quantity_done"]:last:contains("5.00")',
        run: () => {},
    },
    {
        trigger: 'div[name=move_raw_ids] td[name="quantity_done"]:last',
        run: 'click',
    },
    {
        trigger: 'div[name="quantity_done"] input',
        run: 'text 6.0'
    },
    {
        content: "Click Pager",
        trigger: ".o_pager_value:first()",
    },
    {
        trigger: "input[id='qty_producing']",
        run: 'text 8.0',
    },
    {
        content: "Click Pager",
        trigger: ".o_pager_value:first()",
    },
    {
        trigger: 'div[name=move_raw_ids] td[name="quantity_done"]:last:contains("6.00")',
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
        trigger: "input[id='qty_producing']",
        run: 'text 2.0',
    },
    {
        content: "Click Pager",
        trigger: ".o_pager_value:first()",
    },
    {
        trigger: 'div[name=move_raw_ids] td[name="quantity_done"]:last:contains("2.00")',
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
    ...tour.stepUtils.saveForm(),
]);
