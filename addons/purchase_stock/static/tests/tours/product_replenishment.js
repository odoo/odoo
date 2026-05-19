import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_product_replenishment", {
    steps: () => [
        // Show Route column
        {
            content: "Open line fields list",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            content: "Show route column",
            trigger: '.o-dropdown-item input[name="route_id"]',
            run: "check",
        },
        {
            content: "Close line fields list",
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        // Create reordering rule for product 'Book Shelf'
        {
            content: "Click New Button",
            trigger: 'button:contains("New")',
            run: "click",
        },
        {
            content: "Select Product",
            trigger: '.o_selected_row .o_list_many2one[name="product_id"] input',
            run: "edit Book Shelf",
        },
        {
            content: "Valid Product",
            trigger: '.ui-menu-item-wrapper:contains("Book Shelf")',
            run: "click",
        },
        {
            content: "Select Buy Route",
            trigger: '.o_selected_row .o_list_many2one[name="route_id"] input',
            run: "edit Buy",
        },
        {
            content: "Valid Route",
            trigger: '.ui-menu-item-wrapper:contains("Buy")',
            run: "click",
        },
        {
            content: "Save the Rule",
            trigger: 'button:contains("Save")',
            run: "click",
        },
        {
            content: "Wait for the reordering rule to be added",
            trigger:
                '.o_data_row:not(.o_selected_row) td[name="product_id"]:contains("Book Shelf")',
        },
    ],
});
