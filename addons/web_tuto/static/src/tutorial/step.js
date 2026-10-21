import { queryAll } from "@odoo/hoot-dom";

export const INPUT = "input, textarea, [contenteditable=true]";

/**
 * A step of the view of its chapter: a field (`TutorialStepField`) or an
 * action (`TutorialStepAction`), which define `findAnchor(root)` (the element
 * the pointer points at) and `isDoneBy(root, target)` (whether the user's
 * click or focus does the step)
 */
export class TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {string} key the key saving the progress of the user
     * @param {boolean} done
     * @param {TutorialChapter} chapter the chapter the step is done in
     */
    constructor(definition, key, done, chapter) {
        this.key = key;
        this.type = definition.type;
        this.content = definition.content;
        this.hint = Boolean(definition.hint);
        this.tooltipPosition = definition.tooltipPosition || "bottom";
        this.done = done;
        this.chapter = chapter;
        this.tutorial = chapter.tutorial;
        /** The selector of the element of the step */
        this.selector = "";
    }

    /**
     * @param {ParentNode} root
     * @param {Element} source the element the user started to drag
     * @returns {boolean} whether it does the step
     */
    isDoneByDrag(root, source) {
        return false;
    }

    /**
     * @param {ParentNode} root
     * @param {Element} source the element the user dragged
     * @param {PointerEvent} ev the release of the pointer
     * @returns {boolean} whether it does the step
     */
    isDoneByDrop(root, source, ev) {
        return false;
    }

    /**
     * Does the step for the user (Next): focuses its input, or does its
     * action. A hint is only shown.
     * @param {ParentNode} root
     */
    async perform(root) {
        const anchor = this.findAnchor(root);
        if (!anchor || this.hint) {
            return;
        }
        if (anchor.matches(INPUT)) {
            anchor.focus();
        } else {
            await this._act(anchor, root);
        }
    }

    /**
     * Resets the done steps after this one, done again, the tutorial going on
     * from its chapter
     * @returns {TutorialStep[]} the steps reset
     */
    resetNextSteps() {
        const { steps } = this.tutorial;
        const nextSteps = steps.slice(steps.indexOf(this) + 1).filter((nextStep) => nextStep.done);
        for (const nextStep of nextSteps) {
            nextStep.done = false;
        }
        this.tutorial.chapterIndex = this.chapter.index;
        return nextSteps;
    }

    /**
     * Does the action of the step on its anchor, a click by default
     * @param {HTMLElement} anchor
     * @param {ParentNode} root
     * @private
     */
    async _act(anchor, root) {
        anchor.click();
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement | null} the element of the step, unless disabled
     * @private
     */
    _findElement(root) {
        return this._findEnabled(this.selector, root);
    }

    /**
     * @param {string} selector
     * @param {ParentNode} root
     * @returns {HTMLElement | null} the first visible element matching the
     *   selector, unless disabled
     * @private
     */
    _findEnabled(selector, root) {
        return (
            queryAll(selector, { root, visible: true }).find((el) => !el.matches(":disabled")) ||
            null
        );
    }
}
