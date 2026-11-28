import { TutorialStep } from "@web_tutorial/tutorial/tutorial_step";

/**
 * A dialog in the middle of the screen showing the message of the step
 * (`type: "dialog"`, e.g. a welcome message), on no element of the page: done
 * with Next only, like a skippable step
 */
export class TutorialStepDialog extends TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {boolean} done
     * @param {TutorialChapter} chapter
     */
    constructor(definition, done, chapter) {
        super(definition, done, chapter);
        this.skippable = true;
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement} the element of the root, the step being shown in
     *   it whatever it shows
     * @override
     */
    findAnchor(root) {
        return root === document ? document.body : root;
    }

    /**
     * @returns {boolean} false: no element of the page does it
     */
    isDoneBy() {
        return false;
    }
}
