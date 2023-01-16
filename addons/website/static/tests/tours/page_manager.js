/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

const deleteSelectedPage = [
    {
        content: "Click on Action",
        trigger: '.o_cp_action_menus button',
    },
    {
        content: "Click on Delete",
        trigger: '.o-dropdown--menu span:contains("Delete")',
    },
    {
        content: "Click on I am sure about this",
        trigger: 'main.modal-body input[type="checkbox"]',
        // The loading of the dependencies can take a while and
        // sometimes reach the default 10s timeout
        timeout: 20000,
    },
    {
        content: "Click on OK",
        trigger: '.modal-content footer button.btn-primary',
    }
];
const homePage = 'tr:contains("Home")';

wTourUtils.registerWebsitePreviewTour('website_page_manager', {
    test: true,
    url: '/',
}, [
    {
        content: "Click on Site",
        trigger: 'button.dropdown-toggle[title="Site"]',
    },
    {
        content: "Click on Pages",
        trigger: 'a.dropdown-item[data-menu-xmlid="website.menu_website_pages_list"]',
    },
    {
        content: "Click on Home Page",
        trigger: `.o_list_renderer ${homePage} td.o_list_record_selector input[type="checkbox"]`,
    },
    ...deleteSelectedPage,
    {
        content: "Check that the page has been removed",
        trigger: `.o_list_renderer:not(:has(${homePage}))`,
        run: () => null,
    },
    {
        content: "Click on All Pages",
        trigger: '.o_list_renderer thead input[type="checkbox"]',
    },
    ...deleteSelectedPage,
    {
        content: "Check that all pages have been removed",
        trigger: '.o_list_renderer tbody:not(:has([data-id]))',
        run: () => null,
    },
]);
