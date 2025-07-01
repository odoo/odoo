/** @odoo-module **/

import { registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

/**
 * The purpose of these tours is to check whether Publish can or cannot be
 * used by the given current user.
 */

registerWebsitePreviewTour('test_can_publish_partner', {
    edition: false,
    url: '/partners',
}, () => [{
    content: 'Open grade filter',
    trigger: ':iframe .dropdown a.dropdown-toggle:contains("All Categories")',
    run: "click",
}, {
    content: 'Filter on Grade Test', // needed if there are demo data
    trigger: ':iframe .dropdown a.dropdown-item:contains("Grade Test")',
    run: "click",
}, {
    content: 'Go to partner',
    trigger: ':iframe a:contains("Agrolait")',
    run: "click",
}, {
    content: 'Unpublish',
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

registerWebsitePreviewTour('test_cannot_publish_partner', {
    edition: false,
    url: '/partners',
}, () => [{
    content: 'Open grade filter',
    trigger: ':iframe .dropdown a.dropdown-toggle:contains("All Categories")',
    run: "click",
}, {
    content: 'Filter on Grade Test', // needed if there are demo data
    trigger: ':iframe .dropdown a.dropdown-item:contains("Grade Test")',
    run: "click",
}, {
    content: 'Go to partner',
    trigger: ':iframe a:contains("Agrolait")',
    run: "click",
}, {
    content: 'Check there is no Publish/Unpublish',
    trigger: '.o_menu_systray:not(:has(.o_menu_systray_item.o_website_publish_container))',
}]);
