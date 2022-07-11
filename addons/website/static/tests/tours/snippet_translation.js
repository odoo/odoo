/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('snippet_translation', {
    url: '/',
    edition: true,
    test: true,
}, [
    wTourUtils.dragNDrop({name: 'Cover'}),
    {
        content: "Check that contact us contain Parseltongue",
        trigger: 'iframe .s_cover .btn-primary:contains("Contact us in Parseltongue")',
        run: () => null, // it's a check
    },
    {
        content: "Check that the save button contains 'in fu_GB'",
        trigger: '.btn[data-action="save"]:contains("Save in fu_GB")',
        run: () => null, // it's a check
    },
]);
