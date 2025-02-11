/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';

// Note: cannot import @website/../tests/tour_utils/widget_lifecycle_dep_widget
// here because that module requires web.public.widget which is not available
// in the backend, where this tour definition is loaded. Easier to duplicate
// that key for now rather than create a whole file to handle this localStorage
// key only.
const localStorageKey = 'widgetAndWysiwygLifecycle';

wTourUtils.registerWebsitePreviewTour("widget_lifecycle", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_countdown",
        name: "Countdown",
    }),
    {
        content: "Wait for the widget to be started and empty the widgetAndWysiwygLifecycle list",
        trigger: "iframe .s_countdown.public_widget_started",
        run: () => {
            // Start recording the calls to the "start" and "destroy" method of
            // the widget and the wysiwyg.
            window.localStorage.setItem(localStorageKey, '[]');
        },
    },
    ...wTourUtils.clickOnSave(),
    {
        content: "Wait for the widget to be started",
        trigger: "iframe .s_countdown.public_widget_started",
        run: () => {}, // It's a check
    },
    ...wTourUtils.clickOnEditAndWaitEditMode(),
    {
        content: "Wait for the widget to be started and check the order of the lifecycle method call of the widget and the wysiwyg",
        trigger: "iframe .s_countdown.public_widget_started",
        run: () => {
            const result = JSON.parse(window.localStorage.widgetAndWysiwygLifecycle);
            const expected = ["widgetStop", "wysiwygStop", "widgetStart",
                "widgetStop", "wysiwygStart", "wysiwygStarted", "widgetStart",
            ];
            const alternative = ["widgetStop", "widgetStart", "wysiwygStop",
                "widgetStop", "wysiwygStart", "wysiwygStarted", "widgetStart",
            ];
            const resultIsEqualTo = (arr) => {
                return arr.length === result.length
                    && arr.every((item, i) => item === result[i]);
            };
            if (!(resultIsEqualTo(expected) || resultIsEqualTo(alternative))) {
                // The "destroy" method of the wysiwyg is called two times when
                // leaving the edit mode: the first one comes explicitly from
                // the "leaveEditMode" of the "wysiwyg_adapter". The second
                // comes from the OWL mechanism as the wysiwyg is not present in
                // the DOM when the page is reloaded. Because it is not
                // guaranteed that this last call happens before the start of
                // the widget at the page reload, two sequences are acceptable
                // as a result.
                console.error(`
                    Expected: ${expected.toString()}
                    Or:       ${alternative.toString()}
                    Result:   ${result.toString()}
                `);
            }
        },
    },
]);
