import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("website_sale.onboarding_tour_test", {}, () => [
    {
        trigger: ":iframe .o_wsale_products_page",
    },
    {
        trigger: ".o_menu_systray .o_new_content_container > button",
        content: "Let's create your first product.",
        run: "click",
    },
    {
        trigger: "button[data-module-xml-id='base.module_website_sale']",
        content: "Select New Product to create it and manage its properties to boost your sales.",
        run: "click",
    },
    {
        trigger: ".modal-dialog input[type=text]",
        content: "Enter a name for your new product",
        run: "edit Test",
    },
    {
        trigger: ".modal-footer button.btn-primary",
        content: "Click on Save to create the product.",
        run: "click",
    },
    {
        trigger: ".o_builder_sidebar_open",
    },
    {
        trigger: ":iframe .product_price .oe_currency_value:visible",
        content: "Edit the price of this product by clicking on the amount.",
        run: "editor 1.99",
        timeout: 30000,
    },
    {
        trigger: ":iframe .product_price .o_dirty .oe_currency_value:not(:text(1.00))",
    },
    {
        trigger: ":iframe #wrap img.product_detail_img",
        content: "Double click here to set an image describing your product.",
        run: "dblclick",
    },
    {
        trigger: ".o_select_media_dialog .o_upload_media_button",
        content: "Upload a file from your local library.",
        run: "click .modal-footer .btn-secondary",
    },
    {
        trigger: "button[data-name='blocks']",
        content: "Click here to go back to block tab.",
        run: "click",
    },
    {
        trigger: "body:not(.modal-open)",
    },
    {
        trigger: ".o_builder_sidebar_open",
    },
    {
        content: "Click on the Content category.",
        trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="Content"].o_draggable .o_snippet_thumbnail_area`,
        run: "click",
    },
    {
        content: "Click on the Text - Image building block.",
        trigger: `.modal .show:iframe .o_snippet_preview_wrap[data-snippet-id="s_text_image"]:not(.d-none)`,
        run: "click",
    },
    {
        trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
    },
    {
        // Wait until the drag and drop is resolved (causing a history step)
        // before clicking save.
        trigger: ".o-snippets-top-actions button[data-icon='undo']:not([disabled])",
    },
    {
        trigger: "button[data-action=save]",
        content: "Once you click on Save, your product is updated.",
        run: "click",
    },
    {
        trigger: ":iframe body:not(.editor_enable)",
    },
    {
        trigger: ".o_menu_systray_item.o_website_publish_container a",
        content: "Click on this button so your customers can see it.",
        run: "click",
    },
    {
        trigger: "button[data-menu-xmlid='website.menu_reporting']",
        content: "Click here to open the reporting menu",
        run: "click",
    },
    {
        trigger:
            "a[data-menu-xmlid='website.menu_website_dashboard'], a[data-menu-xmlid='website.menu_website_analytics']",
        content: "Let's now take a look at your eCommerce dashboard to get your eCommerce website ready in no time.",
        // Just check during test mode. Otherwise, clicking it will result to random error on loading the Chart.js script.
    },
]);
