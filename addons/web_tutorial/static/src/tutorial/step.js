import { queryAll } from "@odoo/hoot-dom";
import { INPUT } from "@web_tutorial/plugin";

/**
 * A step of the view of its chapter: a field (`TutorialStepField`) or an
 * action (`TutorialStepAction`), which define `isDoneBy(root, target)`
 * (whether the user's click or focus does the step)
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
     * @returns {HTMLElement | null} the element the pointer points at: the
     *   element of the step, unless disabled
     */
    findAnchor(root) {
        const elements = queryAll(this.selector, { root, visible: true });
        return elements.find((el) => !el.matches(":disabled")) || null;
    }

    /**
     * Whether the user starting to drag an element (`source`) does the step,
     * never by default
     * @returns {boolean}
     */
    isDoneByDrag() {
        return false;
    }

    /**
     * Whether the user dropping an element (`root`, `source`, and the release
     * of the pointer `ev`) does the step, never by default
     * @returns {boolean}
     */
    isDoneByDrop() {
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
     * Does the action of the step on its anchor (in `root`), a click by
     * default
     * @param {HTMLElement} anchor
     * @private
     */
    async _act(anchor) {
        anchor.click();
    }
}
