/** @odoo-module **/
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_detailed_op_no_save_1', {  steps: () => [
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
        run: "click",
    },
    {
        trigger: ".modal .o_field_widget[name=lot_name] input",
        run: "edit lot1",
    },
    {
        trigger: ".modal .o_field_widget[name=quantity] input",
        run: "edit 4",
    },
    {
        trigger: ".modal button:contains(save)",
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

registry.category("web_tour.tours").add('test_generate_serial_1', {  steps: () => [
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
        run: "click",
    },
    {
        trigger: ".modal div[name=next_serial] input",
        run: "edit serial_n_1",
    },
    {
        trigger: ".modal div[name=next_serial_count] input",
        run: "edit 5 && click body",
    },
    {
        trigger: ".modal .btn-primary:contains('Generate')",
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

registry.category("web_tour.tours").add('test_generate_serial_2', {  steps: () => [
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
        run: "click",
    },
    // We generate lots for a first batch of 50 products
    {
        trigger: ".modal .o_widget_generate_serials > button",
        run: "click",
    },
    {
        trigger: ".modal h4:contains('Generate Lot numbers')",
        run: "click",
    },
    {
        trigger: ".modal div[name=next_serial] input",
        run: "edit lot_n_1_1",
    },
    {
        trigger: ".modal div[name=next_serial_count] input",
        run: "edit 7.5",
    },
    {
        trigger: ".modal div[name=total_received] input",
        run: "edit 50",
    },
    {
        trigger: ".modal .modal-footer button.btn-primary:contains(Generate)",
        run: "click",
    },
    {
        trigger: ".modal span[data-tooltip=Quantity]:contains(50)",
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
        run: "click",
    },
    {
        trigger: ".modal h4:contains('Generate Lot numbers')",
    },
    {
        trigger: ".modal div[name=next_serial] input",
        run: "edit lot_n_2_1",
    },
    {
        trigger: ".modal div[name=next_serial_count] input",
        run: "edit 13",
    },
    {
        trigger: ".modal div[name=total_received] input",
        run: "edit 50",
    },
    {
        trigger: ".modal div[name=keep_lines] input",
        run: "check",
    },
    {
        trigger: ".modal .modal-footer button.btn-primary:contains(Generate)",
        run: "click",
    },
    {
        trigger: ".modal span[data-tooltip=Quantity]:contains(100)",
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 11){
                console.error("wrong number of move lines generated. " + nbLines + " instead of 11");
            }
        },
    },
    {
        trigger: ".modal .o_form_button_save",
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

registry.category('web_tour.tours').add('test_inventory_adjustment_apply_all', {  steps: () => [
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
        trigger: "body:not(:has(.modal))",
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
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name=lot_name] input",
            run: 'edit two',
        },
        {
            trigger: ".modal .o_form_view.modal-content .o_form_button_save",
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

registry.category("web_tour.tours").add("test_edit_existing_line", {
    steps: () => [
        {
            trigger: ".o_data_cell[name=quantity]",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: "edit 2",
        },
        {
            trigger: ".fa-list",
            run: "click",
        },
        {
            trigger: ".modal h4:contains(Stock move)",
            run: "click",
        },
        {
            trigger: ".modal .o_data_cell[name=quantity]:eq(1)",
            run: "click",
        },
        {
            trigger: ".modal .o_field_widget[name=lot_name] input",
            run: "edit two",
        },
        {
            trigger: ".modal .o_form_view.modal-content .o_form_button_save:enabled",
            run: "click",
        },
        {
            content: "wait the modal is totally closed before click on save",
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ".o_form_view .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_renderer.o_form_saved",
        },
    ],
});

registry.category("web_tour.tours").add('test_edit_existing_lines_2', {
    steps: () => [
        { trigger: ".o_data_row:has(.o_data_cell[data-tooltip='Product a']) .fa-list", run: 'click'},
        { trigger: ".o_data_cell[name=lot_name]", run: 'click' },
        { trigger: ".o_data_cell[name=lot_name] input", run: 'edit SNa001'},
        { trigger: ".o_form_view.modal-content .o_form_button_save", run: 'click'},
        { trigger: "body:not(:has(div .modal-content))"},
        { trigger: ".o_data_row:has(.o_data_cell[data-tooltip='Product b']) .fa-list", run: 'click' },
        { trigger: ".o_data_cell[name=lot_name]", run: 'click' },
        { trigger: ".o_data_cell[name=lot_name] input", run: 'edit SNb001'},
        { trigger: ".o_form_view.modal-content .o_form_button_save", run: 'click'},
        { trigger: "body:not(:has(div .modal-content))"},
        { trigger: ".o_form_view:not(.modal-content) .o_form_button_save", run: 'click' },
        { trigger: ".o_form_renderer.o_form_saved" },
    ]
});

registry.category("web_tour.tours").add('test_onchange_twice_lot_ids', {
    steps: () => [
        {
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Serial Numbers')",
            run: "click",
        },
        {
            trigger: ".o_data_cell.o_many2many_tags_cell",
            run: "click",
        },
        {
            trigger: ".oi-close:first",
            run: "click",
        },
        {
            trigger: ".oi-close:first",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_renderer.o_form_saved",
        },
    ],
});
