/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_stock_picking_batch_sm_to_sml_synchronization", {
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
            content: "Check the modal 'Open: Transfers' is open",
            trigger: ".modal h4:contains(open: transfers)",
        },
        {
            content: "Click in cell to start edition",
            trigger: ".modal:contains(open: transfers) .o_data_row > td:contains('Product A')",
            run: "click",
        },
        {
            trigger: ".modal:contains(open: transfers) .o_list_number > div[name=quantity] input",
            run: "edit 7",
        },
        {
            trigger: ".modal:contains(open: transfers) .fa-list",
            run: "click",
        },
        {
            trigger: ".modal:contains(open: stock move) h4:contains('Stock move')",
            run: "click",
        },
        {
            trigger:
                ".modal:contains(open: stock move) .o_field_pick_from > span:contains('WH/Stock/Shelf A')",
        },
        {
            trigger:
                ".modal:contains(open: stock move) .o_list_footer .o_list_number > span:contains(7)",
        },
        {
            content: "Click Save",
            trigger: ".modal:contains(open: stock move) .o_form_button_save",
            run: "click",
        },
        {
            content: "Click in cell to start edition",
            trigger: ".modal:contains(open: transfers) .o_data_row > td:contains('Product A')",
            run: "click",
        },
        {
            trigger: ".modal:contains(open: transfers) .o_list_number[name=quantity] input",
            run: "edit 21",
        },
        {
            trigger: ".modal:contains(open: transfers) .fa-list",
            run: "click",
        },
        {
            content: "Click in cell to start edition",
            trigger:
                ".modal:contains(open: stock move) .o_field_pick_from > span:contains('WH/Stock/Shelf A')",
            run: "click",
        },
        {
            trigger: ".modal:contains(open: stock move) .o_list_number[name=quantity] input",
            run: "edit 27",
        },
        {
            content: "Click Save",
            trigger: ".modal:contains(open: stock move) .o_form_button_save:contains(save)",
            run: "click",
        },
        {
            content: "Click in cell to start edition",
            trigger: ".modal:contains(open: transfers) .o_data_row > td:contains(47)",
            run: "click",
        },
        {
            trigger: ".modal:contains(open: transfers) .o_field_widget[name=quantity] input",
            run: "edit 7",
        },
        {
            trigger: ".modal:contains(open: transfers) .fa-list",
            run: "click",
        },
        {
            trigger: ".modal:contains(open: stock move) .o_data_row > td:contains(7)",
        },
        {
            content: "Click Save",
            trigger: ".modal:contains(open: stock move) .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".modal:contains(open: transfers) .o_form_button_save",
            run: "click",
        },
    ],
});
