import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_dashboard_refresh", {
    url: "/odoo/ecommerce-orders",
    steps: () => [
        {
            content: "Make sure there are 2 orders to confirm and display them",
            trigger:
                ".o_dashboard_card[title='Orders to Confirm'] .o_dashboard_card_data:contains('2')",
            run: "click",
        },
        {
            trigger: ".o_dashboard_card[title='Orders to Confirm'].active",
        },
        {
            trigger: ".o_list_table .o_data_row:contains('Quotation Sent'):eq(1)",
        },
        {
            content: "Select the first order",
            trigger: ".o_list_table .o_data_row .o-checkbox input",
            run: "click",
        },
        {
            trigger: ".o_data_row_selected",
        },
        {
            content: "Confirm it using the header button",
            trigger: ".o_control_panel button[string='Confirm Orders']",
            run: "click",
        },
        {
            content: "There should only be one order to confirm",
            trigger:
                ".o_dashboard_card[title='Orders to Confirm'] .o_dashboard_card_data:contains('1')",
        },
        {
            content: "Select the second order",
            trigger: ".o_list_table .o_data_row .o-checkbox input",
            run: "click",
        },
        {
            trigger: ".o_data_row_selected",
        },
        {
            trigger: ".o_cp_action_menus button.o-dropdown:contains('Action')",
            run: "click",
        },
        {
            content: "Confirm it using the action",
            trigger: ".o-dropdown-item:contains('Confirm Orders')",
            run: "click",
        },
        {
            content: "There shouldn't be any order to confirm",
            trigger: "body:not(.o_dashboard_card[title='Orders to Confirm'])",
        },
        {
            content: "Make sure there are 2 orders to invoice and display them",
            trigger:
                ".o_dashboard_card[title='Orders to Invoice'] .o_dashboard_card_data:contains('2')",
            run: "click",
        },
        {
            trigger: ".o_dashboard_card[title='Orders to Invoice'].active",
        },
        {
            content: "Select the first order",
            trigger: ".o_list_table .o_data_row .o-checkbox input",
            run: "click",
        },
        {
            trigger: ".o_data_row_selected",
        },
        {
            trigger: ".o_cp_action_menus button.o-dropdown:contains('Action')",
            run: "click",
        },
        {
            content: "Close it using the action",
            trigger: ".o-dropdown-item:contains('Close Invoicing')",
            run: "click",
        },
        {
            content: "There should only be one order to invoice",
            trigger:
                ".o_dashboard_card[title='Orders to Invoice'] .o_dashboard_card_data:contains('1')",
        },
    ],
});
