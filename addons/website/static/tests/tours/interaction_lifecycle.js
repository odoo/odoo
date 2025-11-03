import {
    clickOnEditAndWaitEditMode,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

// Note: cannot import @website/../tests/tour_utils/lifecycle_dep_interaction
// here because that module requires web.public.interaction which is not available
// in the backend, where this tour definition is loaded. Easier to duplicate
// that key for now rather than create a whole file to handle this localStorage
// key only.
const localStorageKey = "interactionAndWysiwygLifecycle";

registerWebsitePreviewTour(
    "interaction_lifecycle",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_countdown",
            name: "Countdown",
            groupName: "Content",
        }),
        {
            content:
                "Wait for the interaction to be started and empty the interactionAndWysiwygLifecycle list",
            trigger: ":iframe .s_countdown.interaction_started",
            run: () => {
                // Start recording the calls to the "start" and "destroy" method
                // of the interaction and the wysiwyg.
                window.localStorage.setItem(localStorageKey, "[]");
            },
        },
        {
            trigger: "button[data-action=save]:enabled:contains(save)",
            run: "click",
        },
        {
            content: "Wait for the interaction to be started",
            trigger: ":iframe .s_countdown.interaction_started",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content:
                "Wait for the interaction to be started and check the order of the lifecycle method call of the interaction and the wysiwyg",
            trigger: ":iframe .s_countdown.interaction_started",
            run() {
                const result = JSON.parse(window.localStorage.interactionAndWysiwygLifecycle);
                const expected = [
                    "interactionStop",
                    "interactionStart",
                    "interactionStop",
                    "interactionStart",
                ];
                const alternative = [
                    "interactionStop",
                    "interactionStart",
                    "wysiwygStop",
                    "interactionStop",
                    "wysiwygStart",
                    "wysiwygStarted",
                    "interactionStart",
                ];
                const resultIsEqualTo = (arr) =>
                    arr.length === result.length && arr.every((item, i) => item === result[i]);
                if (!(resultIsEqualTo(expected) || resultIsEqualTo(alternative))) {
                    // The "destroy" method of the wysiwyg is called two times
                    // when leaving the edit mode: the first one comes
                    // explicitly from the "leaveEditMode" of the
                    // "wysiwyg_adapter". The second comes from the OWL
                    // mechanism as the wysiwyg is not present in the DOM when
                    // the page is reloaded. Because it is not guaranteed that
                    // this last call happens before the start of the
                    // interaction at the page reload, two sequences are
                    // acceptable as a result.
                    console.error(`
                    Expected: ${expected.toString()}
                    Or:       ${alternative.toString()}
                    Result:   ${result.toString()}
                `);
                }
            },
        },
    ]
);
