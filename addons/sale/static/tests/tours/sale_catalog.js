/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('sale_catalog', {
    test: true,
    checkDelay: 50,
    steps: () => [
        {
            content: "Create a new SO",
            trigger: '.o_list_button_add',
            run: 'click',
        },
        {
            content: "Select the customer field",
            trigger: ".o_field_res_partner_many2one input.o_input",
            run: 'click',
        },
        {
            content: "Wait for the field to be active",
            trigger: "input[id*='partner_id']",
        },
        {
            content: "Select a customer from the dropdown",
            trigger: ".dropdown-item",
            run: 'click',
        },
        {
            content: "Open product catalog",
            trigger: '.o_form_view button:contains("Catalog")',
            run: 'click',
        },
        {
            content: "Type 'Restricted' into the search bar",
            trigger: 'input.o_searchview_input',
            run: "text Restricted",
        },
        {
            content: "Search for the product",
            trigger: '.o_searchview_autocomplete .o_menu_item',
        },
        {
            content: "Add the product to the SO",
            trigger: '.o_kanban_record:contains("Restricted Product") .fa-shopping-cart',
            run: 'click',
        },
        {
            content: "Input a custom quantity",
            trigger: '.o_kanban_record:contains("Restricted Product") .o_input',
            run: "text 6",
        },
        {
            content: "Increase the quantity",
            trigger: '.o_kanban_record:contains("Restricted Product") .fa-plus',
            run: 'click',
        },
        {
            content: "Close the catalog",
            trigger: '.o-kanban-button-back',
            run: 'click',
        },
        {
            content: "Confirm the SO",
            trigger: '.o_form_view button:contains("Confirm")',
            run: 'click',
        },
    ]
});
