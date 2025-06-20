import { addSectionFromProductCatalog } from "@account/js/tours/tour_utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('sale_catalog', {
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
            trigger: ".o_field_res_partner_many2one input[aria-expanded=true]",
        },
        {
            content: "Select a customer from the dropdown",
            trigger: ".o_field_res_partner_many2one .dropdown-item:not([id$='_loading']):first",
            run: 'click',
        },
        {
            content: "Open product catalog",
            trigger: 'button[name="action_add_from_catalog"]',
            run: 'click',
        },
        {
            content: "Type 'Restricted' into the search bar",
            trigger: 'input.o_searchview_input',
            run: "edit Restricted",
        },
        {
            content: "Search for the product",
            trigger: 'input.o_searchview_input',
            run: "press Enter",
        },
        {
            content: "Wait for catalog rendering",
            trigger: '.o_kanban_record:contains("Restricted Product")',
        },
        {
            content: "Wait for filtering",
            trigger: '.o_kanban_renderer:not(:has(.o_kanban_record:contains("AAA Product")))',
        },
        {
            content: "Add the product to the SO",
            trigger: '.o_kanban_record:contains("Restricted Product") .fa-shopping-cart',
            run: 'click',
        },
        {
            content: "Wait for product to be added",
            trigger: '.o_kanban_record:contains("Restricted Product"):not(:has(.fa-shopping-cart))',
        },
        {
            content: "Input a custom quantity",
            trigger: '.o_kanban_record:contains("Restricted Product") .o_input',
            run: "edit 6",
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
    ]
});

registry.category("web_tour.tours").add('test_add_section_from_product_catalog_on_sale_order', {
    steps: () => [
        {
            content: "Create a new SO",
            trigger: '.o_list_button_add',
            run: 'click',
        },
        {
            content: "Select the customer field",
            trigger: '.o_field_res_partner_many2one input.o_input',
            run: 'click',
        },
        {
            content: "Wait for the field to be active",
            trigger: '.o_field_res_partner_many2one input[aria-expanded=true]',
        },
        {
            content: "Select a customer from the dropdown",
            trigger: '.o_field_res_partner_many2one .dropdown-item:not([id$="_loading"]):first',
            run: 'click',
        },
        ...addSectionFromProductCatalog(),
    ]
});
