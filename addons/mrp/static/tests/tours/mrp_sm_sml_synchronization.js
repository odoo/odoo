/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from '@web_tour/tour_service/tour_utils';

registry.category("web_tour.tours").add('test_manufacturing_and_byproduct_sm_to_sml_synchronization', {
    test: true,
    steps: () => [
        { trigger: ".btn-primary[name=action_confirm]" },
        { trigger: ".o_data_row > td:contains('product2')" },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Components')" },
        { trigger: ".o_list_number:contains('5')" },
        { trigger: ".o_form_button_save" },
        { trigger: ".o_data_row > td:contains('product2')" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'text 21',
        },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Components')" },
        { trigger: ".o_data_row > td:contains('WH/Stock')" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'text 27',
        },
        { trigger: ".o_form_button_save" },
        { trigger: ".o_data_row > td:contains('43')" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'text 7',
        },
        { trigger: ".fa-list" },
        { trigger: ".o_data_row > td:contains('7')" },
        { trigger: ".o_form_button_save" },
        { trigger: ".nav-link[name=finished_products]" },
        { trigger: ".o_data_row > td:contains('product2')" },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Move Byproduct')" },
        { trigger: ".o_list_number:contains('2')" },
        { trigger: ".o_form_button_save" },
        { trigger: ".o_data_row > td:contains('product2')" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'text 5',
        },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Move Byproduct')" },
        { trigger: ".o_data_row > td:contains('WH/Stock')" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'text 7',
        },
        { trigger: ".o_form_button_save" },
        { trigger: ".o_data_row > td:contains('10')" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'text 8',
        },
        { trigger: ".fa-list" },
        { trigger: ".o_list_footer .o_list_number > span:contains('8')" },
        { trigger: ".o_form_button_save" },
        ...stepUtils.saveForm(),
    ]
});
