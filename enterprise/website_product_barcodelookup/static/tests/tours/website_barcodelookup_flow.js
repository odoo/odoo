import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_01_website_barcodelookup_flow", {
    steps: () => [
        {
            content: "Enter backend",
            trigger: 'a.o_frontend_to_backend_edit_btn',
            run: "click",
        }, {
            content: "Let's create new product using barcode value.",
            trigger: ".o_main_navbar .o-website-btn-custo-secondary",
            run: "click",
        }, {
            content: "Select 'New Product' to create product using barcodelookup.",
            trigger: ".container .fa-shopping-cart",
            run: "click",
        }, {
            content: "Enter barcode value of your product.",
            trigger: ".modal-dialog div[name=barcode] input",
            run: "edit 746775036744",
        }, {
            content: "Click outside of the barcode inputfield.",
            trigger: ".modal-dialog",
            run: "click",
        }, {
            content: "Select category to publish product",
            trigger: '.modal-dialog .o_field_widget[name="public_categ_ids"] input',
            run: "edit Barcode",
        }, {
            content: "Select Barcode Category",
            trigger: '.ui-autocomplete a:contains("Barcode Category")',
            run: "click",
        }, {
            content: "Click on save to create the product.",
            trigger: ".modal-footer button.btn-primary",
            run: "click",
        }, {
            content: "Wait until the modal is closed",
            trigger: "body:not(:has(.modal))",
        },
    ]
});
