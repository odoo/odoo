odoo.define('website.tour.focus_blur_snippets', function (require) {
'use strict';

const ajax = require('web.ajax');
const tour = require('web_tour.tour');

const blockIDToData = {
    parent: {
        selector: '.s_focusblur',
        name: 'section',
        overlayIndex: 2,
    },
    child1: {
        selector: '.s_focusblur_child1',
        name: 'first child',
        overlayIndex: 1,
    },
    child2: {
        selector: '.s_focusblur_child2',
        name: 'second child',
        overlayIndex: 0,
    },
};

function clickAndCheck(blockID, expected) {
    const blockData = blockIDToData[blockID] || {};

    return [{
        content: blockID ? `Enable the ${blockData.name}` : 'Disable all blocks',
        trigger: blockData.selector || '#wrapwrap',
    }, {
        content: 'Once the related overlays are enabled/disabled, check that the focus/blur calls have been correct.',
        trigger: blockID
            ? `.oe_overlay.ui-draggable:eq(${blockData.overlayIndex}).oe_active`
            : `#oe_manipulators:not(:has(.oe_active))`,
        run: function (actions) {
            const result = window.focusBlurSnippetsResult;
            window.focusBlurSnippetsResult = [];

            if (expected.length !== result.length
                    || !expected.every((item, i) => item === result[i])) {
                console.error(`
                    Expected: ${expected.toString()}
                    Result: ${result.toString()}
                `);
            }
        },
    }];
}

window.focusBlurSnippetsResult = [];

tour.register('focus_blur_snippets', {
    test: true,
    url: '/?enable_editor=1',
}, [
    {
        content: 'First load our custom JS options',
        trigger: 'body',
        run: function () {
            ajax.loadJS('/website/static/tests/tour_utils/focus_blur_snippets_options.js').then(function () {
                $('body').addClass('focus_blur_snippets_options_loaded');
            });
        },
    },
    {
        content: 'Drag the custom block into the page',
        trigger: '#snippet_structure .oe_snippet:has(.oe_snippet_body.s_focusblur) .oe_snippet_thumbnail',
        extra_trigger: 'body.focus_blur_snippets_options_loaded',
        run: 'drag_and_drop #wrap',
    },
    ...clickAndCheck('parent', ['focus parent']),
    ...clickAndCheck(null, ['blur parent']),
    ...clickAndCheck('child1', ['focus parent', 'focus child1']),
    ...clickAndCheck('child1', []),
    ...clickAndCheck(null, ['blur parent', 'blur child1']),
    ...clickAndCheck('parent', ['focus parent']),
    ...clickAndCheck('child1', ['blur parent', 'focus parent', 'focus child1']),
    ...clickAndCheck('child2', ['blur parent', 'blur child1', 'focus parent', 'focus child2']),
    ...clickAndCheck('parent', ['blur parent', 'blur child2', 'focus parent']),
]);
});
