import { queryAll } from "@odoo/hoot-dom";
import { INPUT } from "@web_tutorial/tutorial/utils";

/**
 * @typedef {Object} TutorialStepDefinition
 * @property {string} action_name the name of its server action in the
 *   actions menu
 * @property {string} content the help shown by the pointer
 * @property {boolean} hint
 * @property {number} id
 * @property {string} name its field, method, server action (xmlid) or generic
 *   button (e.g. "New"), depending on its type
 * @property {"field"|"generic_button"|"method"|"server_action"} type
 */

/**
 * A step of the view of its chapter: a field (`TutorialStepField`), a button
 * (`TutorialStepButton`) or an item of the actions menu
 * (`TutorialStepMenuItem`)
 */
export class TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {boolean} done
     * @param {TutorialChapter} chapter the chapter the step is done in
     */
    constructor(definition, done, chapter) {
        this.id = definition.id;
        this.type = definition.type;
        this.content = definition.content;
        this.hint = Boolean(definition.hint);
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
     * @abstract
     * @param {ParentNode} root
     * @param {Element} target
     * @returns {boolean} whether the user's click or focus on the target does
     *   the step
     */
    isDoneBy() {
        throw new Error(`${this.constructor.name} must define isDoneBy`);
    }

    /**
     * Does the step for the user (Next): focuses its input, or clicks its
     * element. A hint is only shown.
     * @param {ParentNode} root
     */
    perform(root) {
        const anchor = this.findAnchor(root);
        if (!anchor || this.hint) {
            return;
        }
        if (anchor.matches(INPUT)) {
            anchor.focus();
        } else {
            anchor.click();
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
}
