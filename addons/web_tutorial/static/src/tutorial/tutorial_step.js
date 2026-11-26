import { queryAll } from "@odoo/hoot-dom";
import { INPUT } from "@web_tutorial/tutorial/utils";

/**
 * @typedef {Object} TutorialStepDefinition
 * @property {number|false} action_id the action of its views, if any
 * @property {string} action_name the name of its server action in the
 *   actions menu
 * @property {number} id
 * @property {string} menu_section the xmlid of the section of the navbar
 *   opening its menu
 * @property {import("@odoo/owl").Markup} message the help shown by the
 *   pointer, marked up where read from the session
 * @property {string} name its field, method, server action (xmlid) or generic
 *   button (e.g. "New"), depending on its type; empty for a dialog
 * @property {string} res_model the model of its views, the one of its action
 *   if any
 * @property {boolean} skippable
 * @property {"dialog"|"field"|"generic_button"|"menu_item"|"method"|"server_action"} type
 * @property {string[]} view_types the types of its views (e.g. "form"), all
 *   if empty
 */

/**
 * A step of the view of its chapter: a field (`TutorialStepField`), a button
 * (`TutorialStepButton`), an item of the actions menu (`TutorialStepMenuItem`),
 * a menu of the navbar (`TutorialStepNavbarItem`) or a dialog in the middle
 * of the screen (`TutorialStepDialog`)
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
        this.message = definition.message;
        this.skippable = Boolean(definition.skippable);
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
     * element. A skippable step is only shown.
     * @param {ParentNode} root
     * @param {HTMLElement | null} [anchor] its element, if already found
     */
    perform(root, anchor = this.findAnchor(root)) {
        if (!anchor || this.skippable) {
            return;
        }
        if (anchor.matches(INPUT)) {
            anchor.focus();
        } else {
            anchor.click();
        }
    }
}
