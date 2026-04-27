import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("StockBarcodeBarcodelookupFlow", {
    url: "/web",
    steps: () =>
        [
            {
                trigger: '.o_app[data-menu-xmlid="stock_barcode.stock_barcode_menu"]',
                content: "Open Barcode Module",
                run: "click",
            },
            {
                trigger: '.o_stock_barcode_main_menu .o_button_operations:contains("Operations")',
                content: "Go to Operations",
                run: "click",
            },
            {
                content: "Go to receipts",
                trigger: '.o_kanban_renderer .o_kanban_record .o_kanban_record_title:contains("Receipts")',
                run: "click",
            },
            {
                content: "Create new picking",
                trigger: '.o_control_panel_main_buttons .o-kanban-button-new:contains("New")',
                run: "click",
            },
            {
                content: "Open barcode Filling popup",
                trigger: '.navbar-nav .o_barcode_actions',
                run: 'click',
            },
            {
                content: "Click on Create Product",
                trigger: '.o_barcode_settings button:contains("Create Product")',
                run: 'click',
            },
            {
                content: "Ensure the product creation popup is opened.",
                trigger: '.modal .modal-header:contains("New Product")',
            },
            {
                content: "Fill barcode value",
                trigger: 'div[name="barcode"] input',
                run: 'edit 610532977349',
            },
            // Click outside the input to trigger the onchange event
            {
                content: "Fill barcode value",
                trigger: '.modal .modal-title',
                run: 'click',
            },
            {
                content: "Product name should be filled automatically",
                trigger: 'div[name="name"] input:value("Odoo Scale up")',
            },
            {
                content: "Save the product",
                trigger: '.modal-footer .btn-primary:contains("Save")',
                run: 'click',
            },
            {
                content: "Wait until the modal is closed",
                trigger: "body:not(:has(.modal))",
            },
        ].flat(),
});
