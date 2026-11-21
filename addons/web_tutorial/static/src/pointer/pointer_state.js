import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef TutorialPointerState
 * @property {boolean} [alwaysOpen] whether the bubble is open without hovering
 *   it, e.g. for a hint
 * @property {boolean} [ballHidden] whether only the bubble is shown, e.g. for
 *   a tutorial always showing its tooltips
 * @property {string} [chapterSizes] the number of steps of each chapter of
 *   the tutorial, e.g. "2,3,1", for its progress bar
 * @property {string} [content]
 * @property {boolean} [invalid] whether it points at a field left invalid
 * @property {() => Promise<void>} [onNext]
 * @property {() => void} [onSkip]
 * @property {string} [progress] e.g. "Step 2/12"
 * @property {number} [stepIndex] the index of the step in the tutorial
 * @property {HTMLElement} [trigger]
 * @property {string} [triggerRect] where the trigger is in the window, for
 *   the pointer to follow it when the layout changes (e.g. a field above it
 *   growing)
 */
export const pointerState = proxy({
    alwaysOpen: false,
    ballHidden: false,
    chapterSizes: "",
    content: "",
    invalid: false,
    onNext: undefined,
    onSkip: undefined,
    progress: "",
    stepIndex: -1,
    trigger: undefined,
    triggerRect: "",
});

/** @type {Partial<TutorialPointerState>} the pointer showing nothing */
export const HIDDEN_POINTER = {
    alwaysOpen: false,
    ballHidden: false,
    chapterSizes: "",
    content: "",
    invalid: false,
    onNext: undefined,
    progress: "",
    stepIndex: -1,
    trigger: undefined,
    triggerRect: "",
};

/**
 * @param {{ anchor: HTMLElement, content: string }} invalidField
 * @returns {Partial<TutorialPointerState>}
 */
export function getInvalidFieldPointer(invalidField) {
    return {
        ...HIDDEN_POINTER,
        alwaysOpen: true,
        content: invalidField.content,
        invalid: true,
        trigger: invalidField.anchor,
    };
}

/**
 * @param {TutorialStep | null} step
 * @param {HTMLElement} [trigger]
 * @param {() => Promise<void>} onNext
 * @returns {Partial<TutorialPointerState>}
 */
export function getStepPointer(step, trigger, onNext) {
    if (!step) {
        return HIDDEN_POINTER;
    }
    const { chapters, steps } = step.tutorial;
    const index = steps.indexOf(step);
    return {
        ...HIDDEN_POINTER,
        alwaysOpen: step.hint || step.tutorial.alwaysShowTooltip,
        ballHidden: step.tutorial.alwaysShowTooltip,
        chapterSizes: chapters.map((chapter) => chapter.steps.length).join(","),
        content: step.content,
        onNext,
        progress: _t("Step %(current)s/%(total)s", { current: index + 1, total: steps.length }),
        stepIndex: index,
        trigger,
    };
}
