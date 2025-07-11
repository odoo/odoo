export function addSectionFromProductCatalog() {
    let steps = [];
    steps.push({
        content: "Click Catalog Button",
        trigger: 'button[name=action_add_from_catalog]',
        run: 'click',
    });
    steps.push({
        content: "Open Search Panel if it is closed",
        trigger: '.o_component_with_search_panel',
        run() {
            const button = document.querySelector('.o_search_panel_sidebar button');
            if (button) {
                button.click();
            }
        },
    });
    steps.push({
        content: "Click 'Add Section' button",
        trigger: '.o_search_panel_sections button:contains("+ Add Section")',
        run: 'click',
    });
    steps.push({
        content: "Type new section name",
        trigger: 'input.o_section_input',
        run: 'edit Section A',
    });
    steps.push({
        content: "Press Enter to confirm section",
        trigger: 'input.o_section_input',
        run: 'press Enter',
    });
    steps.push({
        content: "Open Search Panel if it is closed",
        trigger: '.o_component_with_search_panel',
        run() {
            const button = document.querySelector('.o_search_panel_sidebar button');
            if (button) {
                button.click();
            }
        },
    });
    steps.push({
        content: "Add a Product",
        trigger: '.o_kanban_record:contains(Test Product)',
        run: 'click',
    });
    steps.push({
        content: "Close the catalog",
        trigger: '.o-kanban-button-back',
        run: 'click',
    });
    steps.push({
        content: "Ensure Section is first row",
        trigger: '.o_section_and_note_list_view tr:nth-child(1).o_is_line_section',
    });
    steps.push({
        content: "Ensure Product is second row",
        trigger: 'tbody tr:nth-child(2) .o_field_product_label_section_and_note_cell:contains(Test Product)',
    });
    return steps
}
