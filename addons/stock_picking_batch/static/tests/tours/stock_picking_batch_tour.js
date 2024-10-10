/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from '@web_tour/tour_service/tour_utils';

registry.category("web_tour.tours").add('test_stock_picking_batch_sm_to_sml_synchronization', {
    steps: () => [
        {
            trigger: ".btn-primary[name=action_confirm]",
            run: "click",
        },
        {
            trigger: ".o_data_cell[name=name]",
            run: "click",
        },
        {
            trigger: "h4:contains('Transfers')",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('Product A')",
            run: "click",
        },
        {
            trigger: ".o_list_number > div[name=quantity] input",
            run: 'edit 7',
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: "h4:contains('Stock move')",
            run: "click",
        },
        {
            trigger: ".o_field_pick_from > span:contains('WH/Stock/Shelf A')",
            run: "click",
        },
        {
            trigger: ".o_list_footer .o_list_number > span:contains('7')",
            run: "click",
        },
        {
            content: "Click Save",
            trigger: ".modal:not(.o_inactive_modal) .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('Product A')",
            run: "click",
        },
        {
            trigger: ".o_list_number[name=quantity] input",
            run: 'edit 21',
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: "h4:contains('Stock move')",
            run: "click",
        },
        {
            trigger: ".o_field_pick_from > span:contains('WH/Stock/Shelf A')",
            run: "click",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .o_list_number[name=quantity] input",
            run: 'edit 27',
        },
        {
            content: "Click Save",
            trigger: ".modal:not(.o_inactive_modal) .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('47')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'edit 7',
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('7')",
            run: "click",
        },
        {
            content: "Click Save",
            trigger: ".modal:not(.o_inactive_modal) .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        ...stepUtils.saveForm(),
    ]
});
