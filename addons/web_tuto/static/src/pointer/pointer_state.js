import { proxy } from "@odoo/owl";

/**
 * @typedef TutorialPointerState
 * @property {boolean} [alwaysOpen] whether the bubble is open without hovering
 *   it, e.g. for a hint
 * @property {string} [content]
 * @property {boolean} [invalid] whether it points at a field left invalid
 * @property {() => Promise<void>} [onNext]
 * @property {() => void} [onSkip]
 * @property {string} [progress] e.g. "Step 2/12"
 * @property {"top"|"bottom"|"left"|"right"} [side] the side of the trigger the
 *   ball is on
 * @property {boolean} [tipsShown] whether the user always shows the tips
 * @property {HTMLElement} [trigger]
 */
export const pointerState = proxy({
    alwaysOpen: false,
    content: "",
    invalid: false,
    onNext: undefined,
    onSkip: undefined,
    progress: "",
    side: "bottom",
    tipsShown: false,
    trigger: undefined,
});
