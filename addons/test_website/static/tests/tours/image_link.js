/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

/**
 * The purpose of this tour is to check the link on image flow.
 */

const selectImageSteps = [{
    content: "select block",
    trigger: "iframe #wrapwrap .s_text_image",
}, {
    content: "check link popover disappeared",
    trigger: "iframe body:not(:has(.o_edit_menu_popover))",
    run: () => {}, // check
}, {
    content: "select image",
    trigger: "iframe #wrapwrap .s_text_image img",
}];

wTourUtils.registerEditionTour('test_image_link', {
    test: true,
    url: '/',
    edition: true,
}, [
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }),
    ...selectImageSteps,
    {
        content: "enable link",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-customizeblock-option:has(we-title:contains(Media)) we-button.fa-link",
    }, {
        content: "enter site URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "text odoo.com",
    },
    ...selectImageSteps,
    {
        content: "check popover content has site URL",
        trigger: ".o_edit_menu_popover a.o_we_url_link[href='http://odoo.com/']:contains(http://odoo.com/)",
        run: () => {}, // check
    }, {
        content: "remove URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "remove_text",
    },
    ...selectImageSteps,
    {
        content: "check popover content has no URL",
        trigger: ".o_edit_menu_popover a.o_we_url_link:not([href]):contains(No URL specified)",
        run: () => {}, // check
    }, {
        content: "enter email URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "text mailto:test@test.com",
    },
    ...selectImageSteps,
    {
        content: "check popover content has mail URL",
        trigger: ".o_edit_menu_popover:has(.fa-envelope-o) a.o_we_url_link[href='mailto:test@test.com']:contains(mailto:test@test.com)",
        run: () => {}, // check
    }, {
        content: "enter phone URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "text tel:555-2368",
    },
    ...selectImageSteps,
    {
        content: "check popover content has phone URL",
        trigger: ".o_edit_menu_popover:has(.fa-phone) a.o_we_url_link[href='tel:555-2368']:contains(tel:555-2368)",
        run: () => {}, // check
    }, {
        content: "remove URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "remove_text",
    },
    ...selectImageSteps,
    {
        content: "check popover content has no URL",
        trigger: ".o_edit_menu_popover a.o_we_url_link:not([href]):contains(No URL specified)",
        run: () => {}, // check
    },
]);
