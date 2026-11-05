import { queryFirst } from "@odoo/hoot-dom";
import { INPUT, TutorialStep } from "@web_tuto/tutorial/step";

const ADD_LINE_BUTTON = ".o_field_x2many_list_row_add button";

/**
 * A field of the view (of its quick create form, in a kanban view), done
 * once focused by the user. On a x2many field showing its lines, it's done
 * by adding a line.
 */
export class TutorialStepField extends TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {string} key
     * @param {boolean} done
     * @param {TutorialChapter} chapter
     */
    constructor(definition, key, done, chapter) {
        super(definition, key, done, chapter);
        const path = definition.name.split(".");
        this.name = path.pop();
        /** The x2many field whose lines the field is of, if any */
        this.x2many = path[0];
        const scope = chapter.viewType === "kanban" ? ".o_kanban_quick_create " : "";
        this.selector = this.x2many
            ? `${scope}.o_field_widget[name='${this.x2many}'] .o_data_row [name='${this.name}']`
            : `${scope}.o_field_widget[name='${this.name}']:not(.o_field_x2many *)`;
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement | null} its input, or the button adding a line to
     *   a x2many field
     */
    findAnchor(root) {
        const el = this._findElement(root);
        if (!el) {
            return null;
        }
        const anchorSelector = this._isX2many(el) ? ADD_LINE_BUTTON : INPUT;
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
        return !this._isX2many(el) || Boolean(target.closest(ADD_LINE_BUTTON));
    }

    /**
     * @param {Element} el the element of the field
     * @returns {boolean} whether it's a x2many field showing its lines
     * @private
     */
    _isX2many(el) {
        return Boolean(queryFirst(".o_field_x2many", { root: el }));
    }
}
