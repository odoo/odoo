/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from '@web_tour/tour_service/tour_utils';

registry.category("web_tour.tours").add('test_stock_picking_batch_sm_to_sml_synchronization', {
    test: true,
    steps: () => [
        { trigger: ".btn-primary[name=action_confirm]" },
        {
            trigger: ".o_data_cell[name=name]" ,
            run: 'click',
        },
        { trigger: "h4:contains('Transfers')" },
        { trigger: ".o_data_row > td:contains('Product A')" },
        {
            trigger: ".o_list_number[name=quantity] input",
            run: 'text 7',
        },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Stock move')" },
        { trigger: ".o_field_pick_from > span:contains('WH/Stock/Shelf A')" },
        { trigger: ".o_list_footer .o_list_number > span:contains('7')" },
        { trigger: ".o_form_button_save" },
        { trigger: ".o_data_row > td:contains('Product A')" },
        {
            trigger: ".o_list_number[name=quantity] input",
            run: 'text 21',
        },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Stock move')" },
        { trigger: ".o_field_pick_from > span:contains('WH/Stock/Shelf A')" },
        {
            trigger: ".o_list_number[name=quantity] input",
            run: 'text 27',
        },
        { trigger: ".o_form_button_save" },
        { trigger: ".o_data_row > td:contains('47')" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'text 7',
        },
        { trigger: ".fa-list" },
        { trigger: ".o_data_row > td:contains('7')" },
        { trigger: ".o_form_button_save" },
        { trigger: ".o_form_button_save" },
        ...stepUtils.saveForm(),
    ]
});
