import { proxy } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef TutorialPointerState
 * @property {boolean} [alwaysOpen] whether the bubble is open without hovering
 *   it, e.g. for a skippable step
 * @property {boolean} [ballHidden] whether only the bubble is shown, e.g. for
 *   a tutorial expanding its messages
 * @property {boolean} [centered] whether the bubble is in the middle of the
 *   screen, on no trigger, e.g. for a dialog step
 * @property {string} [chapterSizes] the number of steps of each chapter of
 *   the tutorial, e.g. "2,3,1", for its progress bar
 * @property {string|import("@odoo/owl").Markup} [content]
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
/** @type {Partial<TutorialPointerState>} the pointer showing nothing */
export const HIDDEN_POINTER = {
    alwaysOpen: false,
    ballHidden: false,
    centered: false,
    chapterSizes: "",
    content: "",
    invalid: false,
    onNext: undefined,
    progress: "",
    stepIndex: -1,
    trigger: undefined,
    triggerRect: "",
};

export const pointerState = proxy({ ...HIDDEN_POINTER, onSkip: undefined });

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
        return { ...HIDDEN_POINTER };
    }
    const { chapters, steps } = step.tutorial;
    const index = steps.indexOf(step);
    const centered = step.type === "dialog";
    return {
        ...HIDDEN_POINTER,
        alwaysOpen: step.skippable || step.tutorial.expandMessages,
        ballHidden: step.tutorial.expandMessages,
        centered,
        chapterSizes: chapters.map((chapter) => chapter.steps.length).join(","),
        content: step.message,
        onNext,
        progress: _t("Step %(current)s/%(total)s", { current: index + 1, total: steps.length }),
        stepIndex: index,
        trigger: centered ? undefined : trigger,
    };
}
