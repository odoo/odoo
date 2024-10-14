/** @odoo-module **/

import {
    clickOnExtraMenuItem,
    clickOnSave,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

registerWebsitePreviewTour('translate_menu_name', {
    url: '/pa_GB',
    edition: false,
}, () => [
    {
        content: "Open Edit dropdown",
        trigger: '.o_edit_website_container button',
        run: "click",
    },
    {
        content: "activate translate mode",
        trigger: '.o_translate_website_dropdown_item',
        run: "click",
    },
    {
        content: "Close the dialog",
        trigger: '.modal-footer .btn-primary',
        run: "click",
    },
    clickOnExtraMenuItem({}, true),
    {
        content: "translate the menu entry",
        trigger: ':iframe a[href="/englishURL"] span',
        run: "editor value pa-GB",
    },
    ...clickOnSave(),
]);
