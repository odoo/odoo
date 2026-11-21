import { queryFirst } from "@odoo/hoot-dom";
import { TutorialStepButton } from "@web_tutorial/tutorial/tutorial_step_button";
import { TutorialStepField } from "@web_tutorial/tutorial/tutorial_step_field";
import { TutorialStepMenuItem } from "@web_tutorial/tutorial/tutorial_step_menu_item";

/**
 * @param {TutorialStepDefinition} definition
 * @returns {typeof TutorialStep} the class of the step, depending on its type
 *   and, for a generic button, on whether it's in the actions menu
 */
function getStepClass({ name, type }) {
    if (type === "field") {
        return TutorialStepField;
    }
    if (type === "server_action" || name in TutorialStepMenuItem.ICONS) {
        return TutorialStepMenuItem;
    }
    return TutorialStepButton;
}

/**
 * The chapters of a tutorial, as returned by the server (see
 * `web_tutorial.chapter._get_chapter_json`). A chapter is a view, with its
 * steps, each named depending on its type:
 * - `field`: a field of the view (e.g. `partner_id`, or
 *   `order_line.product_id` for a field of the lines of a x2many field), done
 *   once focused; in a kanban view, a field of its quick create (or of the
 *   form, if opened without it);
 * - `method`: the method called by a button of the view, done once clicked;
 * - `server_action`: a server action bound to the model, done once run from
 *   the actions menu;
 * - `generic_button`: a button of the web client, done once clicked: New,
 *   Edit (opening the form of a kanban quick create), or Delete, Duplicate,
 *   Archive and Unarchive of the actions menu.
 * A hint (`hint: true`) is only shown, the user going on with Next.
 *
 * @typedef {Object} TutorialChapterDefinition
 * @property {Object} context values of the context of its view, e.g. the
 *   `default_move_type` of a customer invoice, not to be shown in the views
 *   of the other records of its model (e.g. a vendor bill)
 * @property {number} id
 * @property {string} model
 * @property {TutorialStepDefinition[]} steps
 * @property {"form"|"kanban"|"list"} view_type a list or kanban chapter is
 *   shown in any view of several records of its model
 */

/**
 * A view of a tutorial, with its steps. A form chapter is shown in the forms
 * of its model; a list or kanban chapter in any view of several records of
 * its model; only with the values of its context, if any.
 */
export class TutorialChapter {
    /**
     * @param {TutorialChapterDefinition} definition
     * @param {Set<number>} doneStepIds the ids of the steps the user did
     * @param {Tutorial} tutorial
     * @param {number} index its position in the tutorial
     */
    constructor(definition, doneStepIds, tutorial, index) {
        this.index = index;
        /** The type of its view, e.g. "form" */
        this.viewType = definition.view_type;
        this.context = definition.context;
        this.model = definition.model;
        this.tutorial = tutorial;
        /** @type {TutorialStep[]} */
        this.steps = definition.steps.map((stepDefinition) => {
            const StepClass = getStepClass(stepDefinition);
            return new StepClass(stepDefinition, doneStepIds.has(stepDefinition.id), this);
        });
    }

    /**
     * @returns {TutorialStep[]} its steps when coming back from a next
     *   chapter: the done ones from the last, then the others
     */
    getStepsToGoBack() {
        return [...this.#getDoneStepsFromLast(), ...this.#getStepsToDo()];
    }

    /**
     * @returns {TutorialStep[]} its steps to go on: the ones not done yet,
     *   then the done ones from the last
     */
    getStepsToGoOn() {
        return [...this.#getStepsToDo(), ...this.#getDoneStepsFromLast()];
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
        return Boolean(this.isOfView(view) && queryFirst(`.o_${view.type}_view`, { root }));
    }

    /**
     * @param {DisplayedView} [view]
     * @returns {boolean} whether the view can show the chapter: its model, a
     *   type showing it and the values of its context
     */
    isOfView(view) {
        return Boolean(
            view?.resModel === this.model &&
                this.#isShownByViewType(view.type) &&
                Object.entries(this.context).every(([key, value]) => view.context?.[key] === value)
        );
    }

    #getDoneStepsFromLast() {
        return this.steps.filter((step) => step.done).reverse();
    }

    #getStepsToDo() {
        return this.steps.filter((step) => !step.done);
    }

    /**
     * @param {string} viewType the type of a displayed view
     * @returns {boolean} whether a view of this type can show the chapter: a
     *   form for a chapter of a form, any view showing several records (e.g. a
     *   kanban view) for a chapter of such a view (e.g. a list)
     */
    #isShownByViewType(viewType) {
        return viewType === this.viewType || (viewType !== "form" && this.viewType !== "form");
    }
}
