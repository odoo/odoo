import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_shop_floor_spreadsheet", {
    steps: () => [
    {
        content: 'Select the workcenter the first time we enter in shopfloor',
        trigger: '.form-check:has(input[name="Mountains"])',
        run: "click",
    },
    {
        trigger: '.form-check:has(input[name="Mountains"]:checked)',
    },
    {
        trigger: 'footer.modal-footer button.btn-primary',
        run: "click",
    },
    {
        trigger: '.o_control_panel_actions button:contains("Mountains")',
        run: "click",
    },
    {
        trigger: '.o_control_panel_actions button.active:contains("Mountains")',
    },
    {
        content: 'Start the workorder on header click',
        trigger: '.o_finished_product span:contains("Snow leopard")',
        run: "click",
    },
    {
        content: "Open spreadsheet check action",
        trigger: '.modal:not(.o_inactive_modal) button:contains("Open spreadsheet"):enabled',
        run: "click",
    },
    {
        content: "Open spreadsheet check action",
        trigger: '.o-spreadsheet',
        run: "click",
    },
    {
        content: "Save the check result",
        trigger: '.o_main_navbar button:contains("Save")',
        run: "click",
    },
    {
        content: "Back on the shop floor",
        trigger: '.o_mrp_display',
    },
]});
