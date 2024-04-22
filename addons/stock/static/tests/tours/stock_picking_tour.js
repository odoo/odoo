/** @odoo-module **/
import { TourError } from "@web_tour/tour_service/tour_utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_detailed_op_no_save_1', { test: true, steps: () => [
    {trigger: '.o_field_x2many_list_row_add > a'},
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit Lot",
    },
    {trigger: ".ui-menu-item > a:contains('Product Lot')"},
    {trigger: ".btn-primary[name=action_confirm]"},
    {trigger: ".fa-list"},
    {trigger: "h4:contains('Stock move')"},
    {trigger: '.o_field_x2many_list_row_add > a'},
    {
        trigger: ".o_field_widget[name=lot_name] input",
        run: "edit lot1",
    },
    {
        trigger: ".o_field_widget[name=quantity] input",
        run: "edit 4",
    },
    {trigger: ".o_form_button_save"},
    {trigger: ".o_optional_columns_dropdown_toggle"},
    {
        trigger: 'input[name="picked"]',
        content: 'Check the picked field to display the column on the list view.',
        run: "check",
    },
    {trigger: ".o_data_cell[name=picked]"},
    {
        trigger: ".o_field_widget[name=picked] input",
        run: "check",
    },
    {trigger: ".btn-primary[name=button_validate]"},
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_generate_serial_1', { test: true, steps: () => [
    {trigger: '.o_field_x2many_list_row_add > a'},
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit Serial",
    },
    {trigger: ".ui-menu-item > a:contains('Product Serial')"},
    {trigger: ".btn-primary[name=action_confirm]"},
    {trigger: ".fa-list"},
    {trigger: "h4:contains('Stock move')"},
    {trigger: '.o_widget_generate_serials > button'},
    {trigger: "h4:contains('Generate Serial numbers')"},
    {
        trigger: "div[name=next_serial] input",
        run: "edit serial_n_1",
    },
    {
        trigger: "div[name=next_serial_count] input",
        run: "edit 5 && click body",
    },
    {trigger: ".btn-primary:contains('Generate')"},
    {
        trigger: "span[data-tooltip=Quantity]:contains('5')",
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 5){
                throw new TourError("wrong number of move lines generated. " + nbLines + " instead of 5");
            }
        },
    },
    {trigger: ".o_form_button_save"},
    {trigger: ".o_optional_columns_dropdown_toggle"},
    {
        trigger: 'input[name="picked"]',
        content: 'Check the picked field to display the column on the list view.',
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        },
    },
    {trigger: ".o_data_cell[name=picked]"},
    {
        trigger: ".o_field_widget[name=picked] input",
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        }
    },
    {trigger: ".btn-primary[name=button_validate]"},
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
        isCheck: true,
    },
]});

registry.category("web_tour.tours").add('test_generate_serial_2', { test: true, steps: () => [
    {trigger: '.o_field_x2many_list_row_add > a'},
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: "edit Lot",
    },
    {trigger: ".ui-menu-item > a:contains('Product Lot 1')"},
    {
        trigger: ".o_field_widget[name=product_uom_qty] input",
        run: "edit 100",
    },
    {trigger: ".btn-primary[name=action_confirm]"},
    {trigger: ".fa-list"},
    {trigger: "h4:contains('Stock move')"},
    // We generate lots for a first batch of 50 products
    {trigger: '.o_widget_generate_serials > button'},
    {trigger: "h4:contains('Generate Lot numbers')"},
    {
        trigger: "div[name=next_serial] input",
        run: "edit lot_n_1_1",
    },
    {
        trigger: "div[name=next_serial_count] input",
        run: "edit 7.5 && click body",
    },
    {
        trigger: "div[name=total_received] input",
        run: "edit 50 && click body",
    },
    {trigger: ".btn-primary:contains('Generate')"},
    {
        trigger: "span[data-tooltip=Quantity]:contains('50')",
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 7){
                throw new TourError("wrong number of move lines generated. " + nbLines + " instead of 7");
            }
        },
    },
    // We generate lots for the last 50 products
    {trigger: '.o_widget_generate_serials > button'},
    {trigger: "h4:contains('Generate Lot numbers')"},
    {
        trigger: "div[name=next_serial] input",
        run: "edit lot_n_2_1",
    },
    {
        trigger: "div[name=next_serial_count] input",
        run: "edit 13 && click body",
    },
    {
        trigger: "div[name=total_received] input",
        run: "edit 50 && click body",
    },
    {
        trigger: "div[name=keep_lines] input",
        run: "click",
    },
    {trigger: ".btn-primary:contains('Generate')"},
    {
        trigger: "span[data-tooltip=Quantity]:contains('100')",
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 11){
                throw new TourError("wrong number of move lines generated. " + nbLines + " instead of 11");
            }
        },
    },
    {trigger: ".o_form_button_save"},
    {trigger: ".o_optional_columns_dropdown_toggle"},
    {
        trigger: "input[name='picked']",
        content: "Check the picked field to display the column on the list view.",
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        },
    },
    {trigger: ".o_data_cell[name=picked]"},
    {
        trigger: ".o_field_widget[name=picked] input",
        run: function (actions) {
            if (!this.anchor.checked) {
                actions.click();
            }
        }
    },
    {trigger: ".btn-primary[name=button_validate]"},
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
        isCheck: true,
    },
]});

registry.category('web_tour.tours').add('test_inventory_adjustment_apply_all', { test: true, steps: () => [
    { trigger: '.o_list_button_add' },
    {
        trigger: 'div[name=product_id] input',
        run: "edit Product 1",
    },
    { trigger: '.ui-menu-item > a:contains("Product 1")' },
    {
        trigger: 'div[name=inventory_quantity] input',
        run: "edit 123",
    },
    // Unfocus to show the "New" button again
    { trigger: '.o_searchview_input_container' },
    { trigger: '.o_list_button_add' },
    {
        trigger: 'div[name=product_id] input',
        run: "edit Product 2",
    },
    { trigger: '.ui-menu-item > a:contains("Product 2")' },
    {
        trigger: 'div[name=inventory_quantity] input',
        run: "edit 456",
    },
    { trigger: 'button[name=action_apply_all]' },
    { trigger: '.modal-content button[name=action_apply]' },
    {
        trigger: '.o_searchview_input_container',
        run: () => {
            const applyButtons = document.querySelectorAll('button[name=action_apply_inventory]');
            if (applyButtons.length > 0){
                throw new TourError('Not all quants were applied!');
            }
        },
    },
]});

registry.category("web_tour.tours").add('test_add_new_line', {
    test: true,
    steps: () => [
        {
            extra_trigger: '.o_form_editable',
            trigger: '.o_field_x2many_list_row_add > a'
        },
        {
            trigger: ".o_field_widget[name=product_id] input",
            run: 'edit two',
        },
        { trigger: ".ui-menu-item > a:contains('Product two')" },
        { trigger: ".fa-list:eq(1)" },
        { trigger: "h4:contains('Stock move')" },
        { trigger: '.o_field_x2many_list_row_add > a' },
        {
            trigger: ".o_field_widget[name=lot_name] input",
            run: 'edit two',
        },
        { trigger: ".o_form_view.modal-content .o_form_button_save" },
        { trigger: ".o_form_view:not(.modal-content) .o_form_button_save" },
        {
            trigger: ".o_form_renderer.o_form_saved",
            isCheck: true,
        },
    ]
});

registry.category("web_tour.tours").add('test_edit_existing_line', {
    test: true,
    steps: () => [
        { trigger: ".o_data_cell[name=quantity]" },
        {
            trigger: ".o_field_widget[name=quantity] input",
            run: 'edit 2',
        },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Stock move')" },
        { trigger: ".o_data_cell[name=quantity]:eq(1)" },
        {
            trigger: ".o_field_widget[name=lot_name] input",
            run: 'edit two',
        },
        { trigger: ".o_form_view.modal-content .o_form_button_save" },
        { trigger: ".o_form_view:not(.modal-content) .o_form_button_save" },
        {
            trigger: ".o_form_renderer.o_form_saved",
            isCheck: true,
        },
    ]
});
