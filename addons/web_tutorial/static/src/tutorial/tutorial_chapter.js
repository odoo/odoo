import { queryFirst } from "@odoo/hoot-dom";
import { TutorialStepButton } from "@web_tutorial/tutorial/tutorial_step_button";
import { TutorialStepField } from "@web_tutorial/tutorial/tutorial_step_field";
import { TutorialStepMenuItem } from "@web_tutorial/tutorial/tutorial_step_menu_item";
import { TutorialStepNavbarItem } from "@web_tutorial/tutorial/tutorial_step_navbar_item";
import { TutorialStepDialog } from "@web_tutorial/tutorial/tutorial_step_dialog";

/**
 * @param {TutorialStepDefinition} definition
 * @returns {typeof TutorialStep} the class of the step, depending on its type
 *   and, for a generic button, on whether it's in the actions menu
 */
function getStepClass({ name, type }) {
    if (type === "field") {
        return TutorialStepField;
    }
    if (type === "menu_item") {
        return TutorialStepNavbarItem;
    }
    if (type === "dialog") {
        return TutorialStepDialog;
    }
    if (type === "server_action" || Object.hasOwn(TutorialStepMenuItem.ICONS, name)) {
        return TutorialStepMenuItem;
    }
    return TutorialStepButton;
}

/**
 * The successive steps of a tutorial in the same views of the same model (see
 * `TutorialStepDefinition`), each named depending on its type:
 * - `field`: a field of the form (e.g. `partner_id`, or
 *   `order_line.product_id` for a field of the lines of a x2many field), done
 *   once focused; in a kanban view, a field of its quick create (or of the
 *   form, if opened without it);
 * - `method`: the method called by a button of the view, done once clicked;
 * - `server_action`: a server action bound to the model, done once run from
 *   the actions menu;
 * - `menu_item`: a menu of the app, done once clicked in the navbar;
 * - `generic_button`: a button of the web client, done once clicked: New
 *   (of a list or kanban view), Edit (opening the form of a kanban quick
 *   create), or Delete, Duplicate, Archive and Unarchive of the actions menu;
 * - `dialog`: no element, its message being shown in a dialog in the middle
 *   of the screen, done with Next.
 * A skippable step (`skippable: true`) is only shown, the user going on with
 * Next.
 *
 * A chapter is shown in the views of its action (or, without one, of its
 * model) of its view types (of all types, if none).
 */
export class TutorialChapter {
    /**
     * @param {TutorialStepDefinition[]} stepDefinitions its steps, all in the
     *   same views of the same model
     * @param {Set<number>} doneStepIds the ids of the steps the user did
     * @param {Tutorial} tutorial
     * @param {number} index its position in the tutorial
     */
    constructor(stepDefinitions, doneStepIds, tutorial, index) {
        this.index = index;
        const [{ res_model, view_types }] = stepDefinitions;
        /** The action of its views, if any: the one of its first step having one */
        this.actionId = stepDefinitions.find(({ action_id }) => action_id)?.action_id || false;
        /** The model of its views */
        this.resModel = res_model;
        /** The types of its views, all if empty */
        this.viewTypes = view_types;
        this.tutorial = tutorial;
        /** @type {TutorialStep[]} */
        this.steps = stepDefinitions.map((stepDefinition) => {
            const StepClass = getStepClass(stepDefinition);
            return new StepClass(stepDefinition, doneStepIds.has(stepDefinition.id), this);
        });
    }

    /**
     * @returns {TutorialStep[]} its steps when coming back from a next
     *   chapter: the done ones from the last (but the dialogs, not to show
     *   a welcome message again, doing it again resetting the steps after it),
     *   then the others
     */
    getStepsToGoBack() {
        return [...this.#getDoneStepsFromLast(), ...this.#getStepsToDo()];
    }

    /**
     * @returns {TutorialStep[]} its steps to go on: the ones not done yet,
     *   then the done ones from the last (but the dialogs)
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
     * @returns {boolean} whether the view can show the chapter: a view of its
     *   action (or, without one, of its model) of one of its view types
     */
    isOfView(view) {
        const isOfViews = this.actionId
            ? view?.actionId === this.actionId
            : view?.resModel === this.resModel;
        return Boolean(isOfViews && (!this.viewTypes.length || this.viewTypes.includes(view.type)));
    }

    #getDoneStepsFromLast() {
        return this.steps.filter((step) => step.done && step.type !== "dialog").reverse();
    }

    #getStepsToDo() {
        return this.steps.filter((step) => !step.done);
    }
}
