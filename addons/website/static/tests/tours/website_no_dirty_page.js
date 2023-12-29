/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

wTourUtils.registerWebsitePreviewTour('website_no_dirty_page', {
    test: true,
    url: '/',
    edition: true,
}, [
    wTourUtils.dragNDrop({
        id: "s_text_image",
        name: "Text - Image",
    }), {
        content: "Click on Discard",
        trigger: '.o_we_website_top_actions [data-action="cancel"]',
    }, {
        content: "Check that discarding actually warns when there are dirty changes, and cancel",
        trigger: ".modal-footer .btn-secondary",
    },
    ...wTourUtils.clickOnSave(),
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        // This makes sure the last step about leaving edit mode at the end of
        // this tour makes sense.
        content: "Confirm we are in edit mode",
        trigger: 'body.editor_has_snippets',
        run: () => null,
    }, {
        // Makes sure the dirty flag does not happen after a setTimeout or
        // something like that.
        content: "Click elsewhere and wait for a few ms",
        trigger: 'iframe #wrap',
        run: function (actions) {
            actions.auto();
            setTimeout(() => document.body.classList.add('o_test_delay'), 999);
        },
    }, {
        content: "Click on Discard",
        trigger: '.o_we_website_top_actions [data-action="cancel"]',
        extra_trigger: 'body.o_test_delay',
    }, {
        content: "Confirm we are not in edit mode anymore",
        trigger: 'body:not(.editor_has_snippets)',
        run: () => null,
    },
]);
