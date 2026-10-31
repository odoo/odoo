import { proxy } from "@odoo/owl";

/**
 * @typedef TutorialPointerState
 * @property {HTMLElement} [trigger]
 * @property {string} [content]
 * @property {string} [progress] e.g. "Step 2/12"
 * @property {Direction} [position]
 * @property {boolean} [hint]
 * @property {boolean} [tipsShown] whether the bubble is always open, as for a hint
 * @property {() => void} [onNext]
 * @property {() => void} [onSkip]
 */
export const pointerState = proxy({
    trigger: undefined,
    content: "",
    progress: "",
    position: "bottom",
    hint: false,
    tipsShown: false,
    onNext: undefined,
    onSkip: undefined,
});
