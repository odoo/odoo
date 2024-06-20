/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

const makeSteps = (steps = []) => [
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
    },
    ...steps,
    {
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
];

wTourUtils.registerWebsitePreviewTour('website_no_action_no_dirty_page', {
    test: true,
    url: '/',
    edition: true,
}, () => makeSteps());

wTourUtils.registerWebsitePreviewTour('website_no_dirty_page', {
    test: true,
    url: '/',
    edition: true,
}, () => makeSteps([
    {
        // This has been known to mark the page as dirty because of the "drag
        // the column on image move" feature.
        content: "Click on default image",
        trigger: 'iframe .s_text_image img',
    }, {
        content: "Click on default paragraph",
        trigger: 'iframe .s_text_image h2 + p.o_default_snippet_text',
    }, {
        // TODO this should be done in a dedicated test which would be testing
        // all default snippet texts behaviors. Will be done in master where a
        // task will review this feature.
        content: "Make sure the paragraph still acts as a default paragraph",
        trigger: 'iframe .s_text_image h2 + p.o_default_snippet_text',
        run: () => null,
    }, {
        content: "Click on button",
        trigger: 'iframe .s_text_image .btn',
        run: function (actions) {
            actions.click();
            const el = this.$anchor[0];
            const sel = el.ownerDocument.getSelection();
            sel.collapse(el, 0);
            el.focus();
        },
    },
]));

wTourUtils.registerWebsitePreviewTour('website_no_dirty_lazy_image', {
    test: true,
    url: '/',
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: 's_text_image',
        name: 'Text - Image',
    }), {
        content: "Replace first paragraph, to insert a new link",
        // Ensure the test keeps testing what it should test (eg if we ever
        // remove the lazy loading on those language img))
        extra_trigger: 'iframe img.o_lang_flag[loading="lazy"]',
        trigger: 'iframe #wrap .s_text_image p',
        run: 'text SomeTestText',
    }, {
        content: "Click elsewhere to be sure the editor fully process the new content",
        extra_trigger: 'iframe #wrap .s_text_image p:contains("SomeTestText")',
        trigger: 'iframe #wrap .s_text_image img',
    }, {
        content: "Check that there is no more than one dirty flag",
        extra_trigger: '.o_we_user_value_widget[data-replace-media="true"]',
        trigger: 'iframe body',
        run: function () {
            const dirtyCount = this.$anchor[0].querySelectorAll('.o_dirty').length;
            if (dirtyCount !== 1) {
                console.error(dirtyCount + " dirty flag(s) found");
            } else {
                this.$anchor[0].querySelector('#wrap').classList.add('o_dirty_as_expected');
            }
        },
    }, {
        content: "Check previous step went through correctly about dirty flags",
        trigger: 'iframe #wrap.o_dirty_as_expected',
        run: () => null, // it's a check
    }
]);
