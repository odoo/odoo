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
    {trigger: ".fa-list"},
    {trigger: "h4:contains('Stock move')"},
    {trigger: '.o_field_x2many_list_row_add > a'},
    {
        trigger: ".o_field_widget[name=lot_name] input",
        run: 'text lot1',
    },
    {
        trigger: ".o_field_widget[name=qty_done] input",
        run: 'text 4',
    },
    {trigger: ".o_form_button_save"},
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
        trigger: ".o_field_widget[name=quantity_done]:contains('5')",
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 5){
                throw new TourError("wrong number of move lines generated. " + nbLines + " instead of 5");
            }
        },
    },
    {trigger: ".o_form_button_save"},
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
        run: 'text Serial',
    },
    {trigger: ".ui-menu-item > a:contains('Product Serial')"},
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
        trigger: ".o_field_widget[name=quantity_done]:contains('5')",
        run: () => {
            const nbLines = document.querySelectorAll(".o_field_cell[name=lot_name]").length;
            if (nbLines !== 5){
                throw new TourError("wrong number of move lines generated. " + nbLines + " instead of 5");
            }
        },
    },
    {trigger: ".o_form_button_save"},
    {trigger: ".btn-primary[name=action_confirm]"},
    {trigger: ".btn-primary[name=button_validate]"},
    {
        trigger: ".o_control_panel_actions button:contains('Traceability')",
        isCheck: true,
    },
]});
