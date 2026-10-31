import { queryFirst, waitFor } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

const ADD_LINE_BUTTON = ".o_field_x2many_list_row_add button";
const DROPDOWN_ITEM = ".o-dropdown--menu .o-dropdown-item";

/**
 * A step of a tutorial, as resolved by the server (see
 * `web_tuto.step._resolve_step`)
 * @typedef TutorialStepData
 * @property {number} id the id of the step
 * @property {"field"|"button"} type
 * @property {string} [name] the name of the field or of the button: a button
 *   of the view, or a generic one (e.g. "new"), of the registry
 *   "web_tuto.buttons"
 * @property {string} [x2many] the x2many field whose lines the field is of
 * @property {string} [scope] the selector of the view the field or the button
 *   is looked for in, e.g. ".o_form_view" or ".o_kanban_quick_create"
 * @property {string} content the help shown by the pointer
 * @property {boolean} hint whether the step is only shown to the user, who
 *   goes on with the "Next" button
 * @property {"top"|"bottom"|"left"|"right"} tooltip_position the side of its
 *   element the pointer is on
 * @property {boolean} done whether the user already did the step
 */

/**
 * A step of a tutorial: a field or a button (of the view, or a generic one
 * such as creating a record or sending a message) of the view of its
 * chapter, with the help explaining it. A field is done once focused by the
 * user, a button once clicked; a button opening a dropdown (e.g. a New button
 * proposing templates) once the first item of its menu is clicked.
 */
export class TutorialStep {
    /**
     * @param {TutorialStepData} data
     * @param {TutorialChapter} chapter the chapter the step is done in
     * @param {Tutorial} tutorial
     */
    constructor(data, chapter, tutorial) {
        this.id = data.id;
        this.type = data.type;
        this.name = data.name;
        this.x2many = data.x2many;
        this.scope = data.scope;
        this.content = data.content;
        this.hint = data.hint;
        this.tooltipPosition = data.tooltip_position;
        this.done = data.done;
        this.chapter = chapter;
        this.tutorial = tutorial;
        if (this.type === "field" && this.x2many) {
            this.selector = `${this.scope} .o_field_widget[name='${this.x2many}'] .o_data_row [name='${this.name}']`;
        } else if (this.type === "field") {
            this.selector = `${this.scope} .o_field_widget[name='${this.name}']`;
        } else {
            const button = `button[name='${this.name}']`;
            this.selector =
                registry.category("web_tuto.buttons").get(this.name, null) ||
                `${this.scope} ${button}, .modal-footer ${button}`;
        }
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement | undefined} the element the pointer points at:
     *   the input of a field, or the button adding a line to a x2many field;
     *   the first item of the menu of an open dropdown
     */
    findAnchor(root) {
        const el = queryFirst(this.selector, { root, visible: true });
        if (el && this.type === "field") {
            const anchorSelector = `input, textarea, [contenteditable=true], ${ADD_LINE_BUTTON}`;
            return queryFirst(anchorSelector, { root: el, visible: true }) || el;
        }
        if (el?.matches(".o-dropdown") && el.ariaExpanded === "true") {
            return queryFirst(DROPDOWN_ITEM, { visible: true }) || el;
        }
        return el;
    }

    /**
     * @param {ParentNode} root
     * @param {Element} target the element the user interacted with
     * @returns {boolean} whether the interaction does the step: on its
     *   element, unless it opens a dropdown, or on the first item of the menu
     *   of its open dropdown
     */
    isDoneOn(root, target) {
        const el = target.closest(this.selector);
        if (el && root.contains(el)) {
            return !el.matches(".o-dropdown");
        }
        const anchor = this.findAnchor(root);
        return Boolean(anchor?.matches(DROPDOWN_ITEM) && anchor.contains(target));
    }

    /**
     * Does the step for the user ("Next" button): focuses its field or
     * clicks its element (or the button adding a line to its x2many field, or
     * the first item of the menu of its dropdown), a hint being only shown
     * @param {ParentNode} root
     */
    async perform(root) {
        let anchor = this.findAnchor(root);
        if (!anchor || this.hint) {
            return;
        }
        if (anchor.matches(".o-dropdown")) {
            anchor.click();
            anchor = await waitFor(DROPDOWN_ITEM, { visible: true });
        }
        if (this.type === "field" && !anchor.matches(ADD_LINE_BUTTON)) {
            anchor.focus();
        } else {
            anchor.click();
        }
    }

    /**
     * Does the already done step again: the done steps after it, of its
     * chapter and of the next ones, aren't done anymore, and the tutorial goes
     * on from its chapter
     * @returns {TutorialStep[]} the steps that aren't done anymore
     */
    redo() {
        const { steps } = this.tutorial;
        const nextSteps = steps.slice(steps.indexOf(this) + 1).filter((nextStep) => nextStep.done);
        for (const nextStep of nextSteps) {
            nextStep.done = false;
        }
        this.tutorial.chapterIndex = this.chapter.index;
        return nextSteps;
    }
}
