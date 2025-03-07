import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_orderpoint_list_view_buttons', { steps: () => [
    // Singular 'Snooze'
    {
        content: "Select 'Knife' in 'Shelf A'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Knife') + .o_data_cell[name='location_id']:contains('Shelf A'))",
        run: "click",
    },
    {
        content: "Hit the 'Snooze' button.",
        trigger: "button:contains('Snooze')",
        run: "click",
    },
    {
        content: "Set the snooze date to 1 week from now.",
        trigger: ".o_radio_item:contains('1 Week') > input[type='radio']",
        run: "click",
    },
    {
        content: "Confirm snooze.",
        trigger: "button[name='action_snooze']",
        run: "click",
    },
    // Batch 'Snooze'
    {
        content: "Select 'Knife' in 'Shelf B'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Knife') + .o_data_cell[name='location_id']:contains('Shelf B'))",
        run: "click",
    },
    {
        content: "Select 'Knife' in 'Shelf C'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Knife') + .o_data_cell[name='location_id']:contains('Shelf C'))",
        run: "click",
    },
    {
        content: "Hit the 'Snooze' button.",
        trigger: "button:contains('Snooze')",
        run: "click",
    },
    {
        content: "Set the snooze date to 1 day from now.",
        trigger: ".o_radio_item:contains('1 Day') > input[type='radio']",
        run: "click",
    },
    {
        content: "Confirm snooze.",
        trigger: "button[name='action_snooze']",
        run: "click",
    },
    // Singular 'Order'
    {
        content: "Select 'Wooden Spoon' in 'Shelf A'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Wood)') + .o_data_cell[name='location_id']:contains('Shelf A'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order' button.",
        trigger: ".dropdown-item:contains('Order'):has(+ .dropdown-item:contains('Order To Max'))",
        run: "click",
    },
    // Singular 'Order to Max'
    {
        content: "Select 'Wooden Spoon' in 'Shelf B'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Wood)') + .o_data_cell[name='location_id']:contains('Shelf B'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order to Max' button.",
        trigger: ".dropdown-item:contains('Order To Max')",
        run: "click",
    },
    // Batch 'Order'
    {
        content: "Select 'Steel Spoon' in 'Shelf A'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Steel)') + .o_data_cell[name='location_id']:contains('Shelf A'))",
        run: "click",
    },
    {
        content: "Select 'Fork' in 'Shelf A'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Fork') + .o_data_cell[name='location_id']:contains('Shelf A'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order' button.",
        trigger: ".dropdown-item:contains('Order'):has(+ .dropdown-item:contains('Order To Max'))",
        run: "click",
    },
    // Batch 'Order to Max'
    {
        content: "Select 'Steel Spoon' in 'Shelf B'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Steel)') + .o_data_cell[name='location_id']:contains('Shelf B'))",
        run: "click",
    },
    {
        content: "Select 'Fork' in 'Shelf B'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Fork') + .o_data_cell[name='location_id']:contains('Shelf B'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order to Max' button.",
        trigger: ".dropdown-item:contains('Order To Max')",
        run: "click",
    },
    {
        // To prevent a race condition
        trigger: ".o_content",
    },
]});


registry.category("web_tour.tours").add('test_orderpoint_product_view_buttons', { steps: () => [
    {
        content: "View reordering rules for the product 'Spoon'.",
        trigger: "button[name='action_view_orderpoints']",
        run: "click",
    },
    // Singular 'Snooze'
    {
        content: "Select 'Wooden Spoon' in 'Shelf C'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Wood)') + .o_data_cell[name='location_id']:contains('Shelf C'))",
        run: "click",
    },
    {
        content: "Hit the 'Snooze' button.",
        trigger: "button:contains('Snooze')",
        run: "click",
    },
    {
        content: "Set the snooze date to 1 day from now.",
        trigger: ".o_radio_item:contains('1 Day') > input[type='radio']",
        run: "click",
    },
    {
        content: "Confirm snooze.",
        trigger: "button[name='action_snooze']",
        run: "click",
    },
    // Batch 'Snooze'
    {
        content: "Select 'Steel Spoon' in 'Shelf C'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Steel)') + .o_data_cell[name='location_id']:contains('Shelf C'))",
        run: "click",
    },
    {
        content: "Select 'Plastic Spoon' in 'Shelf C'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Plastic)') + .o_data_cell[name='location_id']:contains('Shelf C'))",
        run: "click",
    },
    {
        content: "Hit the 'Snooze' button.",
        trigger: "button:contains('Snooze')",
        run: "click",
    },
    {
        content: "Set the snooze date to 1 week from now.",
        trigger: ".o_radio_item:contains('1 Week') > input[type='radio']",
        run: "click",
    },
    {
        content: "Confirm snooze.",
        trigger: "button[name='action_snooze']",
        run: "click",
    },
    {
        content: "Make sure other products are not visible in the 'Spoon' reordering rules view after the snooze.",
        trigger: ".o_data_cell[name='product_id']:contains('Knife'):not(:visible)",
    },
    // Singular 'Order'
    {
        content: "Select 'Wooden Spoon' in 'Shelf A'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Wood)') + .o_data_cell[name='location_id']:contains('Shelf A'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order' button.",
        trigger: ".dropdown-item:contains('Order'):has(+ .dropdown-item:contains('Order To Max'))",
        run: "click",
    },
    // Singular 'Order to Max'
    {
        content: "Select 'Wooden Spoon' in 'Shelf B'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Wood)') + .o_data_cell[name='location_id']:contains('Shelf B'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order to Max' button.",
        trigger: ".dropdown-item:contains('Order To Max')",
        run: "click",
    },
    // Batch 'Order'
    {
        content: "Select 'Steel Spoon' in 'Shelf A'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Steel)') + .o_data_cell[name='location_id']:contains('Shelf A'))",
        run: "click",
    },
    {
        content: "Select 'Steel Spoon' in 'Shelf B'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Steel)') + .o_data_cell[name='location_id']:contains('Shelf B'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order' button.",
        trigger: ".dropdown-item:contains('Order'):has(+ .dropdown-item:contains('Order To Max'))",
        run: "click",
    },
    // Batch 'Order to Max'
    {
        content: "Select 'Plastic Spoon' in 'Shelf A'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Plastic)') + .o_data_cell[name='location_id']:contains('Shelf A'))",
        run: "click",
    },
    {
        content: "Select 'Plastic Spoon' in 'Shelf B'.",
        trigger:
            ".o_list_record_selector:has(+ .o_data_cell[name='product_id']:contains('Spoon (Plastic)') + .o_data_cell[name='location_id']:contains('Shelf B'))",
        run: "click",
    },
    {
        content: "Pick the 'Replenish' dropdown menu.",
        trigger: "button:contains('Replenish')",
        run: "click",
    },
    {
        content: "Hit the 'Order to Max' button.",
        trigger: ".dropdown-item:contains('Order To Max')",
        run: "click",
    },
]});
