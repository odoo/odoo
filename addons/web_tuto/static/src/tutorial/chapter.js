import { queryFirst } from "@odoo/hoot-dom";
import { TutorialStep } from "@web_tuto/tutorial/step";
import { isSameViewType } from "@web_tuto/tutorial/utils";

/**
 * A chapter of a tutorial: a view, with the steps done in it. A chapter of a
 * view showing several records (e.g. a list) is shown in all such views of its
 * model (e.g. its kanban view).
 */
export class TutorialChapter {
    /**
     * @param {Object} data the chapter as returned by the server (see
     *   `web_tuto.chapter._get_chapter_json`)
     * @param {Tutorial} tutorial
     */
    constructor(data, tutorial) {
        this.id = data.id;
        /** The type of its view, e.g. "form" */
        this.viewType = data.view_type;
        this.model = data.model;
        this.tutorial = tutorial;
        /** @type {TutorialStep[]} */
        this.steps = data.steps.map((stepData) => new TutorialStep(stepData, this, tutorial));
    }

    /** Its position in the tutorial */
    get index() {
        return this.tutorial.chapters.indexOf(this);
    }

    get isStarted() {
        return this.steps.some((step) => step.done);
    }

    get isDone() {
        return this.steps.every((step) => step.done);
    }

    /**
     * @param {ParentNode} root the document, or the dialog on top of the others
     * @param {Object} [props] the props of the view displayed in the root
     * @returns {boolean} whether the view displayed in the root shows the
     *   chapter
     */
    isShownIn(root, props) {
        return Boolean(
            props?.resModel === this.model &&
                isSameViewType(this.viewType, props.type) &&
                queryFirst(`.o_${props.type}_view`, { root })
        );
    }

    /**
     * @returns {TutorialStep[]} its steps to go on with the chapter: the ones
     *   not done yet, then the done ones from the last, to go back to when
     *   none of the others can be done (e.g. the record failed to be saved)
     */
    getStepsToGoOn() {
        return [...this._getStepsToDo(), ...this._getDoneStepsFromLast()];
    }

    /**
     * @returns {TutorialStep[]} its steps when going back to the chapter from
     *   a next one: the done ones from the last, doing one of them again going
     *   on from there, then the ones not done yet
     */
    getStepsToGoBack() {
        return [...this._getDoneStepsFromLast(), ...this._getStepsToDo()];
    }

    /** @private */
    _getStepsToDo() {
        return this.steps.filter((step) => !step.done);
    }

    /** @private */
    _getDoneStepsFromLast() {
        return this.steps.filter((step) => step.done).reverse();
    }
}
