/** @odoo-module **/

import { registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

import { stepUtils } from "@web_tour/tour_utils";
/**
 * The purpose of these tours is to check whether Publish can or cannot be
 * used by the given current user.
 */

registerWebsitePreviewTour('test_can_publish_partner', {
    edition: false,
    url: '/partners',
}, () => [
    stepUtils.waitIframeIsReady(),
{
    content: 'Open grade filter',
    trigger: ':iframe .dropdown:has(.dropdown-item:contains("Grade Test")) button.dropdown-toggle:contains("All Categories")',
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
}, () => [
    stepUtils.waitIframeIsReady(),
{
    content: 'Open grade filter',
    trigger: ':iframe .dropdown:has(.dropdown-item:contains("Grade Test")) button.dropdown-toggle:contains("All Categories")',
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
    content: 'Wait for the "edit in backend" button to appear before checking the publish button',
    trigger: '.o_menu_systray .o_website_edit_in_backend > a',
    // Seems enough to just wait for that button presence before checking the
    // following step but a bit of delay seems a bit more robust to potential
    // code changes. At least if the rendering flow changes or the tour system
    // changes, this should be enough to trigger a race condition in this test.
    run: () => new Promise(resolve => setTimeout(resolve, 100)),
}, {
    content: 'Check there is no Publish/Unpublish',
    trigger: '.o_menu_systray:has(.o_website_edit_in_backend > a):not(:has(.o_menu_systray_item.o_website_publish_container))',
}]);
