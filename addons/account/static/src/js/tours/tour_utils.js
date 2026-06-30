export function showProductColumn() {
    // Show product column if Sale is not installed.
    return [
        {
            content: "Open line fields list",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            content: "Show product column",
            trigger: '.o-dropdown-item input[name="product_id"], .o-dropdown-item input[name="product_template_id"]',
            run: function (actions) {
                if (!this.anchor.checked) {
                    actions.click();
                }
            },
        },
        {
            content: "Close line fields list",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
    ];
}

export function addSectionFromProductCatalog() {
    return [
        {
            content: "Click Catalog Button",
            trigger: 'button[name=action_add_from_catalog]',
            run: 'click',
        },
        {
            content: "Click 'Add Section' button",
            trigger: '.o_search_panel_sections button:contains("+ Add Section")',
            run: 'click',
        },
        {
            content: "Type new section name",
            trigger: 'input.o_section_input',
            run: 'edit Section A',
        },
        {
            content: "Click anywhere to add the section",
            trigger: '.o_search_panel',
            run: 'click',
        },
        {
            content: "Check section A is selected",
            trigger: '.o_search_panel_sections .o_selected_section:contains("Section A")',
        },
        {
            content: "Add a Product",
            trigger: '.o_kanban_record:contains("Test Product")',
            run: function () {
                setTimeout(() => {
                    [...document.querySelectorAll('.o_kanban_record')].find(el =>
                        el.textContent.includes('Test Product')
                    )?.click();
                }, 1000);
            },
        },
        {
            content: "Wait for product to be added",
            trigger: '.o_kanban_record:contains("Test Product"):not(:has(.fa-shopping-cart))',
        },
        {
            content: "Close the catalog",
            trigger: '.o-kanban-button-back',
            run: 'click',
        },
        ...showProductColumn(),
        {
            content: "Ensure Section is first row",
            trigger: '.o_section_and_note_list_view tr:nth-child(1).o_is_line_section',
        },
        {
            content: "Ensure Product is second row",
            trigger: 'tbody tr:nth-child(2) .o_field_product_label_section_and_note_cell:contains("Test Product")',
        },
    ];
}
