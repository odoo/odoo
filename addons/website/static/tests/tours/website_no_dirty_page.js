/** @odoo-module **/

import { browser } from '@web/core/browser/browser';
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

const makeSteps = (steps = []) => [
    ...insertSnippet({
        id: "s_text_image",
        name: "Text - Image",
        groupName: "Content",
    }), {
        content: "Click on Discard",
        trigger: '.o_we_website_top_actions [data-action="cancel"]',
        run: "click",
    }, {
        content: "Check that discarding actually warns when there are dirty changes, and cancel",
        trigger: ".modal-footer .btn-secondary",
        run: "click",
    },
    ...clickOnSave(),
    ...clickOnEditAndWaitEditMode(),
    {
        // This makes sure the last step about leaving edit mode at the end of
        // this tour makes sense.
        content: "Confirm we are in edit mode",
        trigger: 'body.editor_has_snippets',
    },
    ...steps,
    {
        // Makes sure the dirty flag does not happen after a setTimeout or
        // something like that.
        content: "Click elsewhere and wait for a few ms",
        trigger: ":iframe #wrap",
        async run(actions) {
            // TODO: use actions.click(); instead
            this.anchor.click();
            await new Promise((resolve) => {
                browser.setTimeout(() => {
                    document.body.classList.add("o_test_delay");
                    resolve();
                }, 999);
            });
        },
    },
    {
        trigger: "body.o_test_delay",
    },
    {
        content: "Click on Discard",
        trigger: '.o_we_website_top_actions [data-action="cancel"]',
        run: "click",
    }, {
        content: "Confirm we are not in edit mode anymore",
        trigger: 'body:not(.editor_has_snippets)',
    },
];

registerWebsitePreviewTour('website_no_action_no_dirty_page', {
    url: '/',
    edition: true,
}, () => makeSteps());

registerWebsitePreviewTour('website_no_dirty_page', {
    url: '/',
    edition: true,
}, () => makeSteps([
    {
        // This has been known to mark the page as dirty because of the "drag
        // the column on image move" feature.
        content: "Click on default image",
        trigger: ':iframe .s_text_image img',
        run: "click",
    }, {
        content: "Click on default paragraph",
        trigger: ':iframe .s_text_image h2 + p.o_default_snippet_text',
        run: "click",
    }, {
        // TODO this should be done in a dedicated test which would be testing
        // all default snippet texts behaviors. Will be done in master where a
        // task will review this feature.
        // TODO also test that applying an editor command removes that class.
        content: "Make sure the paragraph still acts as a default paragraph",
        trigger: ':iframe .s_text_image h2 + p.o_default_snippet_text',
    }, {
        content: "Click on button",
        trigger: ':iframe .s_text_image .btn',
        async run(actions) {
            await actions.click();
            const el = this.anchor;
            const sel = el.ownerDocument.getSelection();
            sel.collapse(el, 0);
            el.focus();
        },
    },
]));

registerWebsitePreviewTour('website_no_dirty_lazy_image', {
    url: '/',
    edition: true,
}, () => [
    ...insertSnippet({
        id: 's_text_image',
        name: 'Text - Image',
        groupName: "Content",
    }),
    {
        // Ensure the test keeps testing what it should test (eg if we ever
        trigger: ':iframe img.o_lang_flag[loading="lazy"]',
    },
    {
        content: "Replace first paragraph, to insert a new link",
        // remove the lazy loading on those language img))
        trigger: ':iframe #wrap .s_text_image p',
        run: 'editor SomeTestText',
    },
    {
        trigger: ':iframe #wrap .s_text_image p:contains("SomeTestText")',
    },
    {
        content: "Click elsewhere to be sure the editor fully process the new content",
        trigger: ':iframe #wrap .s_text_image img',
        run: "click",
    },
    {
        trigger: '.o_we_user_value_widget[data-replace-media="true"]',
    },
    {
        content: "Check that there is no more than one dirty flag",
        trigger: ':iframe body',
        run: function () {
            const dirtyCount = this.anchor.querySelectorAll('.o_dirty').length;
            if (dirtyCount !== 1) {
                console.error(dirtyCount + " dirty flag(s) found");
            } else {
                this.anchor.querySelector('#wrap').classList.add('o_dirty_as_expected');
            }
        },
    }, {
        content: "Check previous step went through correctly about dirty flags",
        trigger: ':iframe #wrap.o_dirty_as_expected',
    }
]);
