/** @odoo-module **/
import { TourError } from "@web_tour/tour_service/tour_utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_detailed_op_no_save_1', { test: true, steps: () => [
    {trigger: '.o_field_x2many_list_row_add > a'},
    {
        trigger: ".o_field_widget[name=product_id] input",
        run: 'text Lot',
    },
    {trigger: ".ui-menu-item > a:contains('Product Lot')"},
    {trigger: ".btn-primary[name=action_confirm]"},
    {trigger: ".fa-list"},
    {trigger: "h4:contains('Stock move')"},
    {trigger: '.o_field_x2many_list_row_add > a'},
    {
        trigger: ".o_field_widget[name=lot_name] input",
        run: 'text lot1',
    },
    {
        trigger: ".o_field_widget[name=quantity] input",
        run: 'text 4',
    },
    {trigger: ".o_form_button_save"},
    {trigger: ".o_optional_columns_dropdown_toggle"},
    {
        trigger: 'input[name="picked"]',
        content: 'Check the picked field to display the column on the list view.',
        run: function (actions) {
            if (!this.$anchor.prop('checked')) {
                actions.click(this.$anchor);
            }
        },
    },
    {trigger: ".o_data_cell[name=picked]"},
    {
        trigger: ".o_field_widget[name=picked] input",
        run: function (actions) {
            if (!this.$anchor.prop('checked')) {
                actions.click(this.$anchor);
            }
        }
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
        run: 'text Serial',
    },
    {trigger: ".ui-menu-item > a:contains('Product Serial')"},
    {trigger: ".btn-primary[name=action_confirm]"},
    {trigger: ".fa-list"},
    {trigger: "h4:contains('Stock move')"},
    {trigger: '.o_widget_generate_serials > button'},
    {trigger: "h4:contains('Generate Serials numbers')"},
    {
        trigger: "div[name=next_serial] input",
        run: 'text serial_n_1',
    },
    {
        trigger: "div[name=next_serial_count] input",
        run: 'text 5',
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
            if (!this.$anchor.prop('checked')) {
                actions.click(this.$anchor);
            }
        },
    },
    {trigger: ".o_data_cell[name=picked]"},
    {
        trigger: ".o_field_widget[name=picked] input",
        run: function (actions) {
            if (!this.$anchor.prop('checked')) {
                actions.click(this.$anchor);
            }
        }
    },
    {trigger: ".btn-primary[name=button_validate]"},
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
        isCheck: true,
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
            run: 'text two',
        },
        { trigger: ".ui-menu-item > a:contains('Product two')" },
        { trigger: ".fa-list:eq(1)" },
        { trigger: "h4:contains('Stock move')" },
        { trigger: '.o_field_x2many_list_row_add > a' },
        {
            trigger: ".o_field_widget[name=lot_name] input",
            run: 'text two',
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
            run: 'text 2',
        },
        { trigger: ".fa-list" },
        { trigger: "h4:contains('Stock move')" },
        { trigger: ".o_data_cell[name=quantity]:eq(1)" },
        {
            trigger: ".o_field_widget[name=lot_name] input",
            run: 'text two',
        },
        { trigger: ".o_form_view.modal-content .o_form_button_save" },
        { trigger: ".o_form_view:not(.modal-content) .o_form_button_save" },
        {
            trigger: ".o_form_renderer.o_form_saved",
            isCheck: true,
        },
    ]
});

registry.category("web_tour.tours").add('test_onchange_twice_lot_ids', {
    test: true,
    steps: () => [
        { trigger: ".o_optional_columns_dropdown_toggle" },
        { trigger: ".dropdown-item:contains('Serial Numbers')"},
        { trigger: ".o_data_cell.o_many2many_tags_cell"},
        { trigger: ".oi-close:first"},
        { trigger: ".oi-close:first"},
        { trigger: ".o_form_button_save"},
        {
            trigger: ".o_form_renderer.o_form_saved",
            isCheck: true,
        },
    ]
});

registry.category("web_tour.tours").add("test_add_new_line_in_detailled_op", {
    test: true,
    steps: () => [
        {
            trigger: ".o_list_view.o_field_x2many .o_data_row button[name='Open Move']",
            run: "click",
        },
        {
            trigger: ".modal-content",
            isCheck: true,
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            run: "click",
        },
        {
            content: "Pick LOT001 to create a move line with a quantity of 0.00",
            trigger: ".o_data_row .o_data_cell[name=lot_id]:contains(LOT001)",
            run: "click",
        },
        {
            content: "check that the move contains three lines",
            trigger: ".modal-content:has(.modal-header .modal-title:contains(Open: Stock move)) .o_data_row:nth-child(3)",
            isCheck: true,
        },
        {
            trigger: ".modal-header .modal-title:contains(Open: Stock move)",
            run: "click",
        },
        {
            content: "Check that the first line is associated with LOT001 for a quantity of 0.00",
            trigger:
                ".modal-content .o_data_row:nth-child(1):has(.o_data_cell[name=quant_id]:contains(WH/Stock - LOT001)):has(.o_data_cell[name=quantity]:contains(0.00))",
            isCheck: true,
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            run: "click",
        },
        {
            content: "LOT001 should not appear as it is not available",
            trigger: ".modal-header .modal-title:contains(Add line: Product Lot)",
            run: () => {
                const lines = document.querySelectorAll(".o_data_row .o_data_cell[name=lot_id]");
                if (lines.length !== 2) {
                    throw new TourError(
                        "Wrong number of available quants: " + lines.length + " instead of 2."
                    );
                }
                const lineLOT001 = Array.from(lines).filter((line) =>
                    line.textContent.includes("LOT001")
                );
                if (lineLOT001.length) {
                    throw new TourError("LOT001 shoudld not be displayed as unavailable.");
                }
            },
        },
        {
            content: "Cancel the move line creation",
            trigger: ".modal-header:has(.modal-title:contains(Add line: Product Lot)) .btn-close",
            run: "click",
        },
        {
            content: "Remove the newly created line",
            trigger:
                ".modal-content .o_data_row:nth-child(1):has(.o_data_cell[name=quant_id]:contains(WH/Stock - LOT001)):has(.o_data_cell[name=quantity]:contains(0.00)) .o_list_record_remove",
            run: "click",
        },
        {
            content: "check that the move contains two lines",
            trigger:
                ".modal-content:has(.modal-header .modal-title:contains(Open: Stock move)):not(:has(.o_data_row:nth-child(3)))",
            isCheck: true,
        },
        {
            content: "Check that the first line is associated with LOT001",
            trigger:
                ".modal-content .o_data_row:nth-child(1) .o_data_cell[name=quant_id]:contains(WH/Stock - LOT001)",
            isCheck: true,
        },
        {
            content: "Check that the second line is associated with LOT002",
            trigger:
                ".modal-content .o_data_row:nth-child(2) .o_data_cell[name=quant_id]:contains(WH/Stock - LOT002)",
            isCheck: true,
        },
        {
            content: "Modify the quant associated to the second line to fully use LOT003",
            trigger: ".modal-content .o_data_row:nth-child(2) .o_data_cell[name=quant_id]",
            run: "click",
        },
        {
            trigger: ".modal-content .o_data_row:nth-child(2) .o_field_widget[name=quant_id] input",
            run: "text LOT003",
        },
        {
            trigger: ".dropdown-item:contains(LOT003)",
            run: "click",
        },
        {
            content: "Modify the quantity of the first line from 10 to 8",
            trigger: ".modal-content .o_data_row:nth-child(1) .o_data_cell[name=quantity]",
            run: "click",
        },
        {
            trigger: ".modal-content .o_data_row:nth-child(1) .o_data_cell[name=quantity] .o_input",
            run: "text 8",
        },
        {
            trigger: ".modal-header .modal-title:contains(Open: Stock move)",
            run: "click",
        },
        {
            trigger: ".modal-content .o_list_number:contains(18.00)",
            isCheck: true,
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            run: "click",
        },
        {
            content: "LOT003 should not appear as it is not available",
            trigger: ".modal-header .modal-title:contains(Add line: Product Lot)",
            run: () => {
                const lines = document.querySelectorAll(".o_data_row .o_data_cell[name=lot_id]");
                if (lines.length !== 2) {
                    throw new TourError(
                        "Wrong number of available quants: " + lines.length + " instead of 2."
                    );
                }
                const lineLOT003 = Array.from(lines).filter((line) =>
                    line.textContent.includes("LOT003")
                );
                if (lineLOT003.length) {
                    throw new TourError("LOT003 shoudld not be displayed as unavailable.");
                }
            },
        },
        {
            content: "Pick LOT001 to create a move line with a quantity of 2.00",
            trigger: ".o_data_row .o_data_cell[name=lot_id]:contains(LOT001)",
            run: "click",
        },
        {
            trigger: ".modal-content .o_list_number:contains(20.00)",
            isCheck: true,
        },
        {
            trigger: ".modal-header .modal-title:contains(Open: Stock move)",
            run: "click",
        },
        {
            content: "Check that 2 units of LOT001 were added",
            trigger:
                ".o_data_row:has(.o_data_cell[name=quant_id]:contains(WH/Stock - LOT001)) .o_data_cell[name=quantity]:contains(2.00)",
            isCheck: true,
        },
        {
            content: "Check that the third line is associated with LOT003",
            trigger:
                ".modal-content .o_data_row:nth-child(3) .o_data_cell[name=quant_id]:contains(WH/Stock - LOT003)",
            isCheck: true,
        },
        {
            content: "Modify the quant associated to the third line to use LOT002",
            trigger: ".modal-content .o_data_row:nth-child(3) .o_data_cell[name=quant_id]",
            run: "click",
        },
        {
            trigger: ".modal-content .o_data_row:nth-child(3) .o_field_widget[name=quant_id] input",
            run: "text LOT002",
        },
        {
            trigger: ".dropdown-item:contains(LOT002)",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains(Open: Stock move)",
            run: "click",
        },
        {
            trigger:
                ".modal-content .o_data_row:nth-child(3) .o_data_cell[name=quant_id]:contains(LOT002)",
            run() {},
        },
        {
            content: "Modify the quantity of the first line from 10 to 15 to change the demand",
            trigger: ".modal-content .o_data_row:nth-child(3) .o_data_cell[name=quantity]",
            run: "click",
        },
        {
            trigger: ".modal-content .o_data_row:nth-child(3) .o_data_cell[name=quantity] .o_input",
            run: "text 15",
        },
        {
            trigger: ".modal-header .modal-title:contains(Open: Stock move)",
            run: "click",
        },
        {
            contnet: "Remove the LOT001 line with a quantity of 8.00",
            trigger:
                ".o_data_row:has(.o_data_cell[name=quantity]:contains(8.00)) .o_list_record_remove",
            run: "click",
        },
        {
            trigger: ".modal-content .o_list_number:contains(17.00)",
            isCheck: true,
        },
        {
            trigger: ".o_field_x2many_list_row_add > a",
            run: "click",
        },
        {
            content: "LOT002 should not appear as it is not available",
            trigger: ".modal-header .modal-title:contains(Add line: Product Lot)",
            run: () => {
                const lines = document.querySelectorAll(".o_data_row .o_data_cell[name=lot_id]");
                if (lines.length !== 2) {
                    throw new TourError(
                        "Wrong number of available quants: " + lines.length + " instead of 2."
                    );
                }
                const lineLOT002 = Array.from(lines).filter((line) =>
                    line.textContent.includes("LOT002")
                );
                if (lineLOT002.length) {
                    throw new TourError("LOT002 shoudld not be displayed as unavailable.");
                }
            },
        },
        {
            content: "Pick LOT001 to create move line to fullfill the demand of 3",
            trigger: ".o_data_row .o_data_cell[name=lot_id]:contains(LOT001)",
            run: "click",
        },
        {
            trigger: ".modal-content .o_list_number:contains(20.00)",
            isCheck: true,
        },
        {
            trigger: ".modal-header .modal-title:contains(Open: Stock move)",
            run: "click",
        },
        {
            content: "Check that 3 units of LOT001 were added",
            trigger:
                ".o_data_row:has(.o_data_cell[name=quant_id]:contains(WH/Stock - LOT001)) .o_data_cell[name=quantity]:contains(3.00)",
            isCheck: true,
        },
        {
            trigger: ".modal-content .o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
        },
        {
            trigger: ".o_form_renderer.o_form_saved",
            isCheck: true,
        },
    ],
});
