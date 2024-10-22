/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from '@web_tour/tour_service/tour_utils';

registry.category("web_tour.tours").add('test_manufacturing_and_byproduct_sm_to_sml_synchronization', {
    steps: () => [
        {
            trigger: ".btn-primary[name=action_confirm]",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('product2')",
            run: "click",
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: "h4:contains('Components')",
            run: "click",
        },
        {
            trigger: ".modal .o_list_number:contains(5)",
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('product2')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'edit 21',
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: "h4:contains('Components')",
            run: "click",
        },
        {
            trigger: ".modal .modal-body .o_data_row > td:contains('WH/Stock')",
            run: "click",
        },
        {
            trigger: ".modal .modal-body .o_field_widget[name=quantity] input",
            run: 'edit 27',
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('43')",
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
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".nav-link[name=finished_products]",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('product2')",
            run: "click",
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: "h4:contains('Move Byproduct')",
            run: "click",
        },
        {
            trigger: ".modal .modal-body .o_data_row > td:contains('WH/Stock')",
            run: "click",
        },
        {
            trigger: ".modal .modal-body .o_field_widget[name=quantity] input",
            run: 'edit 2',
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('product2')",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'edit 5',
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: "h4:contains('Move Byproduct')",
            run: "click",
        },
        {
            trigger: ".modal .modal-body .o_data_row > td:contains('WH/Stock')",
            run: "click",
        },
        {
            trigger: ".modal .modal-body .o_field_widget[name=quantity] input",
            run: 'edit 7',
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_data_row > td:contains('10')",
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
            trigger: ".o_list_footer .o_list_number > span:contains('7')",
            run: "click",
        },
        {
            content: "Click Save",
            trigger: ".modal .modal-footer .o_form_button_save",
            run: "click",
        },
        ...stepUtils.saveForm(),
    ]
});
