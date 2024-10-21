import { insertSnippet, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

/**
 * The purpose of this tour is to check the link on image flow.
 */

const selectImageSteps = [{
    content: "select block",
    trigger: ":iframe #wrapwrap .s_text_image",
    run: "click",
}, {
    content: "check link popover disappeared",
    trigger: ":iframe body:not(:has(.o_edit_menu_popover))",
}, {
    content: "select image",
    trigger: ":iframe #wrapwrap .s_text_image img",
    run: "click",
}];

registerWebsitePreviewTour('test_image_link', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    ...selectImageSteps,
    {
        content: "enable link",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-customizeblock-option:has(we-title:contains(Media)) we-button.fa-link",
        run: "click",
    }, {
        content: "enter site URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "edit odoo.com && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has site URL",
        trigger: ":iframe .o_edit_menu_popover a.o_we_url_link[href='http://odoo.com/']:contains(http://odoo.com/)",
    }, {
        content: "remove URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "clear && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has no URL",
        trigger: ":iframe .o_edit_menu_popover a.o_we_url_link:not([href]):contains(No URL specified)",
    }, {
        content: "enter email URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "edit mailto:test@test.com && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has mail URL",
        trigger: ":iframe .o_edit_menu_popover:has(.fa-envelope-o) a.o_we_url_link[href='mailto:test@test.com']:contains(mailto:test@test.com)",
    }, {
        content: "enter phone URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "edit tel:555-2368 && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has phone URL",
        trigger: ":iframe .o_edit_menu_popover:has(.fa-phone) a.o_we_url_link[href='tel:555-2368']:contains(tel:555-2368)",
    }, {
        content: "remove URL",
        trigger: "#oe_snippets we-customizeblock-options:has(we-title:contains('Image')) we-input:contains(Your URL) input",
        run: "clear && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has no URL",
        trigger: ":iframe .o_edit_menu_popover a.o_we_url_link:not([href]):contains(No URL specified)",
    },
]);
