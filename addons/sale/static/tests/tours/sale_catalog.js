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
        {
            content: "Open Home menu",
            trigger: 'a.o_menu_toggle[href="/odoo"][title="Home menu"]',
            run: 'click',
        },
        {
            content: "Open Settings",
            trigger: 'a.o_app[data-menu-xmlid="base.menu_administration"]',
            run: 'click',
        },
        {
            content: "Search for Units of Measure & Packagings",
            trigger: 'input.o_searchview_input[role="searchbox"]',
            run: 'edit Units of Measure & Packagings',
        },
        {
            content: "Enable Units of Measure & Packagings",
            trigger: 'input.form-check-input[id^="group_uom_"]',
            run: 'check',
        },
        {
            content: "Save settings",
            trigger: 'button.o_form_button_save[data-hotkey="s"]',
            run: 'click',
        },
        {
            content: "Wait for re-render",
            trigger: 'button.o_form_button_save[data-hotkey="s"]',
        },
        {
            content: "Open Home menu",
            trigger: 'a.o_menu_toggle[href="/odoo"][title="Home menu"]',
            run: 'click',
        },
        {
            content: "Open Sales app",
            trigger: 'a.o_app[data-menu-xmlid="sale.sale_menu_root"]',
            run: 'click',
        },
        {
            content: "Open the latest sales order",
            trigger: 'td[name="name"]',
            run: 'click',
        },
        {
            content: "Open the Product",
            trigger: 'div.o_many2one a:contains("Restricted Product")', 
            run: "click",
        },
        {
            content: "Click on sales page",
            trigger: '.o_notebook_headers a:contains("Sales")',
            run: "click",
        },
        {
            content: "Open the Packagings dropdown",
            trigger: 'input.o-autocomplete--input[id^="uom_ids_"][aria-expanded="false"]', 
            run: "click",
        },
        {
            content: "Choose different unit",
            trigger: 'a.dropdown-item.ui-menu-item-wrapper:contains("Pack of 6")', 
            run: "click",
        },
        {
            content: "Go back to quotation",
            trigger: '.o_back_button', 
            run: "click",
        },
        {
            content: "Click on the unit",
            trigger: 'div.o_many2one > span:contains("Units")',
            run: "click",
        },
        {
            content: "Click on the selected unit",
            trigger: 'div.o_field_widget[name="product_uom_id"] input.o-autocomplete--input',
            run: "click",
        },
        {
            content: "Select 'Pack of 6' from the dropdown",
            trigger: "a.dropdown-item.ui-menu-item-wrapper:contains('Pack of 6')",
            run: "click",
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
            content: "Check price per product unit",
            trigger: "span.d-flex.text-muted.small",
        },
    ]
});
