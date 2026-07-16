export function editShopConfiguration(shop) {
    return [
        {
            trigger: "body",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_main_navbar span:contains('Configuration')",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Point of Sales')",
            run: "click",
        },
        {
            trigger: `.o_data_cell[data-tooltip=${shop}]`,
            run: "click",
        },
    ];
}

export function openShopSession(shop) {
    return [
        {
            trigger: ".o_main_navbar .o-dropdown-item:contains('Dashboard')",
            run: "click",
        },
        {
            trigger: `.o_kanban_record:contains(${shop}) .btn-primary`,
            run: "click",
            expectUnloadPage: true,
        },
    ];
}

export function saveConfiguration() {
    return [
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
    ];
}

export function openProductForm(name) {
    return [
        {
            trigger: ".o_main_navbar span:contains('Products')",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Products')",
            run: "click",
        },
        {
            trigger: `.o_kanban_record:contains("${name}")`,
            run: "click",
        },
        {
            trigger: `.o_form_renderer`,
        },
    ];
}

export function clickNotebookTab(name) {
    return [
        {
            content: `Open the ${name} notebook tab`,
            trigger: `.o_notebook a.nav-link:contains("${name}")`,
            run: "click",
        },
    ];
}

export function openListRowFormView(fieldName) {
    return [
        {
            content: `Open the first ${fieldName} record in its form view`,
            trigger: `.o_field_widget[name="${fieldName}"] .o_data_row .o_list_record_open_form_view`,
            run: "click",
        },
    ];
}

export function followMany2oneLink(fieldName) {
    return [
        {
            content: `Follow the internal link of ${fieldName}`,
            trigger: `.o_field_widget[name="${fieldName}"] a`,
            run: "click",
        },
    ];
}
