import { insertSnippet, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';

/**
 * The purpose of this tour is to check the link on image flow.
 */

const selectImageSteps = [{
    content: "select block",
    trigger: ":iframe #wrapwrap .s_text_image",
    async run(helpers) {
        await helpers.click();
        const el = this.anchor;
        const sel = el.ownerDocument.getSelection();
        sel.collapse(el, 0);
        el.focus();
    },
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
        trigger: ".o_customize_tab [data-container-title='Image'] button[data-action-id='setLink']",
        run: "click",
    }, {
        content: "enter site URL",
        trigger: ".o_customize_tab [data-container-title='Image'] div[data-action-id='setUrl'] input",
        run: "edit odoo.com && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has site URL",
        trigger: ".o-we-linkpopover a.o_we_url_link[href='http://odoo.com']:contains(http://odoo.com)",
    }, {
        content: "remove URL",
        trigger: ".o_customize_tab [data-container-title='Image'] div[data-action-id='setUrl'] input",
        run: "clear && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has no URL",
        trigger: ".o-we-linkpopover .o_we_href_input_link:value()",
    }, {
        content: "enter email URL",
        trigger: ".o_customize_tab [data-container-title='Image'] div[data-action-id='setUrl'] input",
        run: "edit mailto:test@test.com && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has mail URL",
        trigger: ".o-we-linkpopover:has(.fa-envelope-o) a.o_we_url_link[href='mailto:test@test.com']:contains(mailto:test@test.com)",
    }, {
        content: "enter phone URL",
        trigger: ".o_customize_tab [data-container-title='Image'] div[data-action-id='setUrl'] input",
        run: "edit tel:555-2368 && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has phone URL",
        trigger: ".o-we-linkpopover:has(.fa-phone) a.o_we_url_link[href='tel:555-2368']:contains(tel:555-2368)",
    }, {
        content: "remove URL",
        trigger: ".o_customize_tab [data-container-title='Image'] div[data-action-id='setUrl'] input",
        run: "clear && click body",
    },
    ...selectImageSteps,
    {
        content: "check popover content has no URL",
        trigger: ".o-we-linkpopover .o_we_href_input_link:value()",
    },
]);
