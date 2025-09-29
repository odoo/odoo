import { stepUtils } from "@web_tour/tour_utils";
import { registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('website_sale_restricted_editor_ui', {
    url: `/shop`,
}, () => [
    {
        content: "Open the site menu to check what is inside",
        trigger: '[data-menu-xmlid="website.menu_site"]',
        run: "click",
    },
    {
        // Not very robust but still nice to have an extra check as this is the
        // main purpose of this tour
        content: "First check the user is not a designer",
        trigger: '.dropdown-menu:has([data-menu-xmlid="website_sale.menu_product_pages"]):not(:has([data-menu-xmlid="website.menu_website_pages_list"]))',
        run: "click",
    },
    {
        // Wait for the possibility to edit to appear
        trigger: ".o_menu_systray button:contains('Edit')",
    },
    {
        content: "Ensure the publish and 'edit-in-backend' buttons are not shown",
        trigger: '.o_menu_systray:not(:has(.form-switch)):not(:has(.o_website_edit_in_backend))',
        run: "click",
    },
    stepUtils.waitIframeIsReady(),
    {
        content: "Navigate to the first product",
        trigger: ':iframe .oe_product_image_link',
        run: "click",
    },
    {
        content: "Click on publish/unpublish",
        trigger: '.o_website_publish_container a:has(input:checked)',
        run: "click",
    },
    {
        trigger:
            ".o_menu_systray_item:not([data-processing]) .form-switch:has(input:not(:checked))",
    },
    {
        content: "Click on edit-in-backend",
        trigger: '.o_menu_systray .o_website_edit_in_backend a',
        run: "click",
    },
    {
        content: "Check that you landed on a form view and that the record was unpublished",
        trigger: '.o-form-buttonbox [name="is_published"] .fa-globe.text-danger',
    },
]);
