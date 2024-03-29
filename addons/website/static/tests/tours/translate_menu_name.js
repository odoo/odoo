/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

wTourUtils.registerWebsitePreviewTour('translate_menu_name', {
    url: '/pa_GB',
    test: true,
    edition: false,
}, () => [
    {
        content: "Open Edit dropdown",
        trigger: '.o_edit_website_container button',
    },
    {
        content: "activate translate mode",
        trigger: '.o_translate_website_dropdown_item',
    },
    {
        content: "Close the dialog",
        trigger: '.modal-footer .btn-primary',
    },
    wTourUtils.clickOnExtraMenuItem({}, true),
    {
        content: "translate the menu entry",
        trigger: ':iframe a[href="/englishURL"] span',
        run: "editor value pa-GB",
    },
    ...wTourUtils.clickOnSave(),
]);
