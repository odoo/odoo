/** @odoo-module */

import { registry } from '@web/core/registry';

registry.category('web_tour.tours').add('test_get_all_rates', {
    steps: () => [
        {
            trigger: 'button[name="action_open_delivery_wizard"]',
            run: 'click',
        },
        {
            trigger: 'div[name="carrier_id"] input',
            content: 'Select the carrier in the wizard',
            run: 'click',
        },
        {
            trigger: 'ul.ui-autocomplete a:contains("Normal Delivery Charges")',
            content: 'Click on the dropdown item',
            run: 'click',
        },
        {
            trigger: 'button:contains("Get all rates")',
            content: 'click "Get all rates" button',
            run: 'click',
        },
        {
            trigger: 'ul.ui-autocomplete',
            content: 'check that many2many carrier_id list is opened',
        },
        {
            trigger: 'body:not(:has(button:contains("Get all rates")))',
            content: 'check that there is no Get all rates button',
        },
        {
            trigger: 'div[name="total_weight"] input',
            content: 'change total weight',
            run: 'edit 15.0',
        },
        {
            trigger: 'div[name="carrier_id"] input',
            content: 'select the carrier in the wizard',
            run: 'click',
        },
        {
            trigger: 'button:contains("Get all rates")',
            content: 'verify "Get all rates" button appears again',
        },
        {
            trigger: 'button[name="button_confirm"]',
            content: 'click the confirm button to add shipping',
            run: 'click',
        },
        {
            trigger: 'body:not(:has(.modal))',
            content: 'wait for the delivery wizard modal to close',
        },
        {
            trigger: '.o_form_saved',
            content: 'wait for the save request to complete',
        },
    ]
});