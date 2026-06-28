import { _t } from "@web/core/l10n/translation";
import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

import { markup } from "@odoo/owl";

registerWebsitePreviewTour("website_sale.onboarding_tour", {}, () => [
    {
        trigger: ":iframe .o_wsale_products_page",
    },
    {
        trigger: ".o_menu_systray .o_new_content_container > button",
        content: _t("Let's create your first product."),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: "button[data-module-xml-id='base.module_website_sale']",
        content: markup(
            _t(
                "Select <b>New Product</b> to create it and manage its properties to boost your sales."
            )
        ),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: ".modal-dialog input[type=text]",
        content: _t("Enter a name for your new product"),
        tooltipPosition: "left",
        run: "edit Test",
    },
    {
        trigger: ".modal-footer button.btn-primary",
        content: markup(_t("Click on <em>Save</em> to create the product.")),
        tooltipPosition: "right",
        run: "click",
    },
    {
        trigger: ".o_builder_sidebar_open",
    },
    {
        trigger: ":iframe .product_price .oe_currency_value:visible",
        content: _t("Edit the price of this product by clicking on the amount."),
        tooltipPosition: "bottom",
        run: "editor 1.99",
        timeout: 30000,
    },
    {
        trigger: ":iframe .product_price .o_dirty .oe_currency_value:not(:text(1.00))",
    },
    {
        trigger: ":iframe #wrap img.product_detail_img",
        content: _t("Double click here to set an image describing your product."),
        tooltipPosition: "top",
        run: "dblclick",
    },
    {
        isActive: ["auto"],
        trigger: ".o_select_media_dialog .o_upload_media_button",
        content: _t("Upload a file from your local library."),
        tooltipPosition: "bottom",
        run: "click .modal-footer .btn-secondary",
    },
    {
        trigger: "button[data-name='blocks']",
        content: _t("Click here to go back to block tab."),
        run: "click",
    },
    {
        trigger: "body:not(.modal-open)",
    },
    {
        trigger: ".o_builder_sidebar_open",
    },
    {
        content: markup(_t("Click on the <b>Content</b> category.")),
        trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="Content"].o_draggable .o_snippet_thumbnail_area`,
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        content: markup(_t("Click on the <b>Text - Image</b> building block.")),
        trigger: `.modal .show:iframe .o_snippet_preview_wrap[data-snippet-id="s_text_image"]:not(.d-none)`,
        tooltipPosition: "top",
        run: "click",
    },
    {
        trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
    },
    {
        // Wait until the drag and drop is resolved (causing a history step)
        // before clicking save.
        trigger: ".o-snippets-top-actions button.fa-undo:not([disabled])",
    },
    {
        trigger: "button[data-action=save]",
        content: markup(_t("Once you click on <b>Save</b>, your product is updated.")),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: ":iframe body:not(.editor_enable)",
    },
    {
        trigger: ".o_menu_systray_item.o_website_publish_container a",
        content: _t("Click on this button so your customers can see it."),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger: "button[data-menu-xmlid='website.menu_reporting']",
        content: _t("Click here to open the reporting menu"),
        tooltipPosition: "bottom",
        run: "click",
    },
    {
        trigger:
            "a[data-menu-xmlid='website.menu_website_dashboard'], a[data-menu-xmlid='website.menu_website_analytics']",
        content: _t(
            "Let's now take a look at your eCommerce dashboard to get your eCommerce website ready in no time."
        ),
        tooltipPosition: "bottom",
        // Just check during test mode. Otherwise, clicking it will result to random error on loading the Chart.js script.
    },
]);
