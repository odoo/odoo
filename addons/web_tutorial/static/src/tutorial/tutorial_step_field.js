import { queryFirst } from "@odoo/hoot-dom";
import { TutorialStep } from "@web_tutorial/tutorial/tutorial_step";
import { INPUT } from "@web_tutorial/tutorial/utils";

/** The first button below the lines, adding a line (not a section or a note) */
const ADD_LINE_BUTTON = ".o_field_x2many_list_row_add button:first-of-type";

/**
 * A field of the form (also of the quick create of a kanban view), done once
 * focused by the user. On a x2many field showing its lines, it's done by
 * adding a line.
 */
export class TutorialStepField extends TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {boolean} done
     * @param {TutorialChapter} chapter
     */
    constructor(definition, done, chapter) {
        super(definition, done, chapter);
        const [x2many, name] = definition.name.includes(".")
            ? definition.name.split(".")
            : [null, definition.name];
        this.selector = x2many
            ? `.o_form_view .o_field_widget[name='${x2many}'] .o_data_row [name='${name}']`
            : `.o_form_view .o_field_widget[name='${name}']:not(.o_field_x2many *)`;
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement | null} its input, or the button adding a line to
     *   a x2many field
     * @override
     */
    findAnchor(root) {
        const el = super.findAnchor(root);
        if (!el) {
            return null;
        }
        const anchorSelector = this.#isX2many(el) ? ADD_LINE_BUTTON : INPUT;
        return queryFirst(anchorSelector, { root: el, visible: true }) || el;
    }

    /**
     * @param {ParentNode} root
     * @param {Element} target
     * @returns {boolean} whether the target is in the field (its button adding
     *   a line, for a x2many field)
     */
    isDoneBy(root, target) {
        const el = target.closest(this.selector);
        if (!el || !root.contains(el)) {
            return false;
        }
        return !this.#isX2many(el) || Boolean(target.closest(ADD_LINE_BUTTON));
    }

    /**
     * @param {Element} el the element of the field
     * @returns {boolean} whether it's a x2many field showing its lines
     */
    #isX2many(el) {
        return Boolean(queryFirst(".o_field_x2many", { root: el }));
    }
}
