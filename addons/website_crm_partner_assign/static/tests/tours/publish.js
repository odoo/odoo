/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

/**
 * The purpose of these tours is to check whether Publish can or cannot be
 * used by the given current user.
 */

wTourUtils.registerWebsitePreviewTour('test_can_publish_partner', {
    edition: false,
    test: true,
}, () => [{
    content: "Unpublish",
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_publish_container:contains("Published")',
    run: "click",
}, {
    content: "Wait for Unpublish",
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_publish_container:contains("Unpublished"):not([data-processing])',
}, {
    content: "Publish",
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_publish_container:contains("Unpublished")',
    run: "click",
}, {
    content: "Wait for Publish",
    trigger: '.o_menu_systray .o_menu_systray_item.o_website_publish_container:contains("Published"):not([data-processing])',
}]);
