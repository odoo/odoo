/** @odoo-modules */

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('website_sale_restricted_editor_ui', {
    test: true,
    url: `/shop`,
}, [
    {
        content: "Open the site menu to check what is inside",
        trigger: '[data-menu-xmlid="website.menu_site"]',
    },
    {
        // Not very robust but still nice to have an extra check as this is the
        // main purpose of this tour
        content: "First check the user is not a designer",
        trigger: '.dropdown-menu:has([data-menu-xmlid="website_sale.menu_product_pages"]):not(:has([data-menu-xmlid="website.menu_website_pages_list"]))',
    },
    {
        content: "Ensure the publish and 'edit-in-backend' buttons are not shown",
        trigger: '.o_menu_systray:not(:has(.o_switch_danger_success)):not(:has(.o_website_edit_in_backend))',
        // Wait for the possibility to edit to appear
        extra_trigger: '.o_menu_systray .o_edit_website_container a',
    },
    {
        content: "Navigate to the first product",
        trigger: 'iframe .oe_product_image_link',
    },
    {
        content: "Click on publish/unpublish",
        trigger: '.o_menu_systray_item .o_switch_danger_success:has(input:checked)',
    },
    {
        content: "Click on edit-in-backend",
        trigger: '.o_menu_systray .o_website_edit_in_backend a',
        extra_trigger: '.o_menu_systray_item:not([data-processing]) .o_switch_danger_success:has(input:not(:checked))',
    },
    {
        content: "Check that you landed on a form view and that the record was unpublished",
        trigger: '.o_form_sheet [name="is_published"] .fa-globe.text-danger',
        run: () => {},
    },
]);
