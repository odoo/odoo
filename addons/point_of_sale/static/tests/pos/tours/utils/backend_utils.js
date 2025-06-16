export function editShopConfiguration(shop) {
    return [
        {
            trigger: ".o_main_navbar span:contains('Configuration')",
            run: "click",
            willUnload: "continue",
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

export function saveShopConfiguration() {
    return [
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
    ];
}
