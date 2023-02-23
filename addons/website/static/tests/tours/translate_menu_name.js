/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('translate_menu_name', {
    url: '/pa_GB',
    test: true,
    edition: false,
}, [
    {
        content: "activate translate mode",
        trigger: '.o_translate_website_container a',
    },
    {
        content: "Close the dialog",
        trigger: '.modal-footer .btn-primary',
    },
    wTourUtils.clickOnExtraMenuItem({}, true),
    {
        content: "translate the menu entry",
        trigger: 'iframe a[href="/englishURL"] span',
        run: 'text value pa-GB',
    },
    ...wTourUtils.clickOnSave(),
]);
