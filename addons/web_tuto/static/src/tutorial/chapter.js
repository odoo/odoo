import { queryFirst } from "@odoo/hoot-dom";
import { TutorialStepAction } from "@web_tuto/tutorial/step_action";
import { TutorialStepField } from "@web_tuto/tutorial/step_field";

/**
 * A view of a tutorial, with its steps. A form chapter is shown in the forms
 * of its model; a list or kanban chapter in any view of several records of
 * its model.
 */
export class TutorialChapter {
    /**
     * @param {TutorialChapterDefinition} definition
     * @param {string[]} stepKeys the keys of its steps
     * @param {Set<string>} doneStepKeys the keys of the steps the user did
     * @param {Tutorial} tutorial
     */
    constructor(definition, stepKeys, doneStepKeys, tutorial) {
        /** The type of its view, e.g. "form" */
        this.viewType = definition.viewType;
        this.model = definition.model;
        this.tutorial = tutorial;
        /** @type {TutorialStep[]} */
        this.steps = definition.steps.map((stepDefinition, index) => {
            const StepClass =
                stepDefinition.type === "field" ? TutorialStepField : TutorialStepAction;
            const key = stepKeys[index];
            return new StepClass(stepDefinition, key, doneStepKeys.has(key), this);
        });
    }

    /**
     * @returns {TutorialStep[]} its steps when coming back from a next
     *   chapter: the done ones from the last, then the others
     */
    getStepsToGoBack() {
        return [...this._getDoneStepsFromLast(), ...this._getStepsToDo()];
    }

    /**
     * @returns {TutorialStep[]} its steps to go on: the ones not done yet,
     *   then the done ones from the last
     */
    getStepsToGoOn() {
        return [...this._getStepsToDo(), ...this._getDoneStepsFromLast()];
    }

    /** Its position in the tutorial */
    get index() {
        return this.tutorial.chapters.indexOf(this);
    }

    get isDone() {
        return this.steps.every((step) => step.done);
    }

    /**
     * @param {ParentNode} root the document, or the dialog on top of the others
     * @param {DisplayedView} [view] the view displayed in the root
     * @returns {boolean} whether the view displayed in the root shows the
     *   chapter
     */
    isShownIn(root, view) {
        return Boolean(
            view?.resModel === this.model &&
                this._isShownByViewType(view.type) &&
                queryFirst(`.o_${view.type}_view`, { root })
        );
    }

    get isStarted() {
        return this.steps.some((step) => step.done);
    }

    /** @private */
    _getDoneStepsFromLast() {
        return this.steps.filter((step) => step.done).reverse();
    }

    /** @private */
    _getStepsToDo() {
        return this.steps.filter((step) => !step.done);
    }

    /**
     * @param {string} viewType the type of a displayed view
     * @returns {boolean} whether a view of this type can show the chapter: a
     *   form for a chapter of a form, any view showing several records (e.g. a
     *   kanban view) for a chapter of such a view (e.g. a list)
     * @private
     */
    _isShownByViewType(viewType) {
        return viewType === this.viewType || (viewType !== "form" && this.viewType !== "form");
    }
}
