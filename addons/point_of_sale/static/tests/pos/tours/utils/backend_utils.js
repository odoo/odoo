export function editShopConfiguration(shop) {
    return [
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

export function openCustomerForm(name) {
    return [
        {
            trigger: ".o_main_navbar span:contains('Orders')",
            run: "click",
        },
        {
            trigger: ".dropdown-item:contains('Customers')",
            run: "click",
        },
        {
            trigger: ".o_facet_values",
            run: "click",
        },
        {
            trigger: ".o_searchview_facet .o_facet_remove",
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
