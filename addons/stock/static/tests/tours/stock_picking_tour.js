/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_detailed_op_no_save_1', { test: true, steps: () => [
    {
        trigger: '.o_field_x2many_list_row_add > a',
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit Lot",
    },
    {
        trigger: ".ui-menu-item > a:contains('Product Lot')",
        run: "click",
    },
    {
        trigger: ".btn-primary[name=action_confirm]",
        run: "click",
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
        trigger: ".modal .o_field_x2many_list_row_add > a",
        in_modal: false,
        run: "click",
    },
    {
        trigger: ".modal .o_field_widget[name=lot_name] input",
        in_modal: false,
        run: "edit lot1",
    },
    {
        trigger: ".modal .o_field_widget[name=quantity] input",
        in_modal: false,
        run: "edit 4",
    },
    {
        trigger: ".modal button:contains(save)",
        in_modal: false,
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        trigger: ".o_optional_columns_dropdown_toggle",
        run: "click",
    },
    {
        trigger: 'input[name="picked"]',
        content: 'Check the picked field to display the column on the list view.',
        run: "check",
    },
    {
        trigger: ".o_data_cell[name=picked]",
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=picked] input",
        run: "check",
    },
    {
        trigger: ".btn-primary[name=button_validate]",
        run: "click",
    },
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
    },
]});

registry.category("web_tour.tours").add('test_generate_serial_1', { test: true, steps: () => [
    {
        trigger: '.o_field_x2many_list_row_add > a',
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit Serial",
    },
    {
        trigger: ".ui-menu-item > a:contains('Product Serial')",
        run: "click",
    },
    {
        trigger: ".btn-primary[name=action_confirm]",
        run: "click",
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
        trigger: '.o_widget_generate_serials > button',
        run: "click",
    },
    {
        trigger: ".modal h4:contains('Generate Serial numbers')",
        in_modal: false,
        run: "click",
    },
    {
        trigger: ".modal div[name=next_serial] input",
        in_modal: false,
        run: "edit serial_n_1",
    },
    {
        trigger: ".modal div[name=next_serial_count] input",
        in_modal: false,
        run: "edit 5 && click body",
    },
    {
        trigger: ".modal .btn-primary:contains('Generate')",
        in_modal: false,
        run: "click",
    },
    {
        trigger: "span[data-tooltip=Quantity]:contains('5')",
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 5){
                console.error("wrong number of move lines generated. " + nbLines + " instead of 5");
            }
        },
    },
    {
        trigger: ".modal button:contains(save)",
        in_modal: false,
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        trigger: ".o_optional_columns_dropdown_toggle",
        run: "click",
    },
    {
        trigger: 'input[name="picked"]',
        content: 'Check the picked field to display the column on the list view.',
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        },
    },
    {
        trigger: ".o_data_cell[name=picked]",
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=picked] input",
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        }
    },
    {
        trigger: ".btn-primary[name=button_validate]",
        run: "click",
    },
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
    },
]});

registry.category("web_tour.tours").add('test_generate_serial_2', { test: true, steps: () => [
    {
        trigger: '.o_field_x2many_list_row_add > a',
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit Lot",
    },
    {
        trigger: ".ui-menu-item > a:contains('Product Lot 1')",
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=product_uom_qty] input",
        run: "edit 100",
    },
    {
        trigger: ".btn-primary[name=action_confirm]",
        run: "click",
    },
    {
        trigger: ".fa-list",
        run: "click",
    },
    {
        trigger: ".modal h4:contains('Stock move')",
        in_modal: false,
        run: "click",
    },
    // We generate lots for a first batch of 50 products
    {
        trigger: ".modal .o_widget_generate_serials > button",
        in_modal: false,
        run: "click",
    },
    {
        trigger: ".modal h4:contains('Generate Lot numbers')",
        in_modal: false,
        run: "click",
    },
    {
        trigger: ".modal div[name=next_serial] input",
        in_modal: false,
        run: "edit lot_n_1_1",
    },
    {
        trigger: ".modal div[name=next_serial_count] input",
        in_modal: false,
        run: "edit 7.5",
    },
    {
        trigger: ".modal div[name=total_received] input",
        in_modal: false,
        run: "edit 50",
    },
    {
        trigger: ".modal .modal-footer button.btn-primary:contains(Generate)",
        in_modal: false,
        run: "click",
    },
    {
        trigger: ".modal span[data-tooltip=Quantity]:contains(50)",
        in_modal: false,
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 7){
                console.error("wrong number of move lines generated. " + nbLines + " instead of 7");
            }
        },
    },
    // We generate lots for the last 50 products
    {
        trigger: ".modal .o_widget_generate_serials > button",
        in_modal: false,
        run: "click",
    },
    {
        trigger: ".modal h4:contains('Generate Lot numbers')",
        in_modal: false,
    },
    {
        trigger: ".modal div[name=next_serial] input",
        in_modal: false,
        run: "edit lot_n_2_1",
    },
    {
        trigger: ".modal div[name=next_serial_count] input",
        in_modal: false,
        run: "edit 13",
    },
    {
        trigger: ".modal div[name=total_received] input",
        in_modal: false,
        run: "edit 50",
    },
    {
        trigger: ".modal div[name=keep_lines] input",
        in_modal: false,
        run: "check",
    },
    {
        trigger: ".modal .modal-footer button.btn-primary:contains(Generate)",
        in_modal: false,
        run: "click",
    },
    {
        trigger: ".modal span[data-tooltip=Quantity]:contains(100)",
        in_modal: false,
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 11){
                console.error("wrong number of move lines generated. " + nbLines + " instead of 11");
            }
        },
    },
    {
        trigger: ".modal .o_form_button_save",
        in_modal: false,
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        trigger: ".o_optional_columns_dropdown_toggle",
        run: "click",
    },
    {
        trigger: "input[name='picked']",
        content: "Check the picked field to display the column on the list view.",
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        },
    },
    {
        trigger: ".o_data_cell[name=picked]",
        run: "click",
    },
    {
        trigger: ".o_field_widget[name=picked] input",
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        }
    },
    {
        trigger: ".btn-primary[name=button_validate]",
        run: "click",
    },
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
    },
]});

registry.category('web_tour.tours').add('test_inventory_adjustment_apply_all', { test: true, steps: () => [
    {
        trigger: '.o_list_button_add',
        run: "click",
    },
    {
        trigger: 'div[name=product_id] input',
        run: "edit Product 1",
    },
    {
        trigger: '.ui-menu-item > a:contains("Product 1")',
        run: "click",
    },
    {
        trigger: 'div[name=inventory_quantity] input',
        run: "edit 123",
    },
    // Unfocus to show the "New" button again
    {
        trigger: '.o_searchview_input_container',
        run: "click",
    },
    {
        trigger: '.o_list_button_add',
        run: "click",
    },
    {
        trigger: 'div[name=product_id] input',
        run: "edit Product 2",
    },
    {
        trigger: '.ui-menu-item > a:contains("Product 2")',
        run: "click",
    },
    {
        trigger: 'div[name=inventory_quantity] input',
        run: "edit 456",
    },
    {
        trigger: 'button[name=action_apply_all]',
        run: "click",
    },
    {
        trigger: '.modal-content button[name=action_apply]',
        run: "click",
    },
    {
        trigger: '.o_searchview_input_container',
        run: () => {
            const applyButtons = document.querySelectorAll('button[name=action_apply_inventory]');
            if (applyButtons.length > 0){
                console.error('Not all quants were applied!');
            }
        },
    },
]});

registry.category("web_tour.tours").add('test_add_new_line', {
    test: true,
    steps: () => [
        {
            trigger: ".o_form_editable",
        },
        {
            trigger: '.o_field_x2many_list_row_add > a',
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=product_id] input",
            run: 'edit two',
        },
        {
            trigger: ".ui-menu-item > a:contains('Product two')",
            run: "click",
        },
        {
            trigger: ".fa-list:eq(1)",
            run: "click",
        },
        {
            trigger: "h4:contains('Stock move')",
            run: "click",
        },
        {
            trigger: ".modal .o_field_x2many_list_row_add > a",
            in_modal: false,
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name=lot_name] input",
            in_modal: false,
            run: 'edit two',
        },
        {
            trigger: ".modal .o_form_view.modal-content .o_form_button_save",
            in_modal: false,
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ".o_form_view .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_renderer.o_form_saved",
        },
    ]
});

registry.category("web_tour.tours").add('test_edit_existing_line', {
    test: true,
    steps: () => [
        {
            trigger: ".o_data_cell[name=quantity]",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'edit 2',
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
            trigger: ".o_data_cell[name=quantity]:eq(1)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=lot_name] input",
            run: 'edit two',
        },
        {
            trigger: ".o_form_view.modal-content .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_view:not(.modal-content) .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_renderer.o_form_saved",
        },
    ]
});
