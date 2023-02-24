/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";
const { onMounted, useState, onRendered, useRef } = owl;

const UNTITLED_TODO_NAME = _lt("Untitled to-do");
const WIDTH_MARGIN = 3;
const PADDING_RIGHT = 5;
const PADDING_LEFT = PADDING_RIGHT - WIDTH_MARGIN;

/**
 *  The FormController is overrided to be able to manage the edition of the name of a to-do directly
 *  in the breadcrumb as well as the mark as done button next to it.
 */

export class TodoFormController extends FormController {
    setup() {
        super.setup();
        this.untitled_name = UNTITLED_TODO_NAME;
        this.placeholder = this.untitled_name;
        this.input = useRef("recordNameInput");

        this.state_todo = useState({
            inputSize: 1,
            isUntitled: true,
            isDone: false,
        });

        onMounted(() => {
            this.isDone = false;
            this.state_todo.isDone = this.isDone;

            this.field_input = document.getElementsByClassName("o_todo_breadcrumb_name_input")[0];
            this.field_input.value = this.name;
            this._setInputSize(this.name);
        });

        onRendered(() => {
            this.env.config.setDisplayName(this.displayName());
            if (!this.not_reload_name) {
                this.name = (this.model.root) ? this.model.root.data.display_name || "": "";
            }
            this.state_todo.isUntitled = this._isUntitled(this.name);
            this.saved_name = this.name;
            if (this.field_input) { // Can possibly be improved (a glitch show the old name at the moment for a fraction of second when saving the record)
                this.field_input.value = this.name;
                this._setInputSize(this.name);
            }
            this.not_reload_name = false;
            //TO-DO : Reload done state if needed (mark as done)
        });
            
    }

    async saveButtonClicked(params = {}) {
        this.saved_name = this.model.root.data.name || this.saved_name;
        super.saveButtonClicked(params);
    }

    async discard() {
        this.name = this.saved_name || this.untitled_name;
        this.field_input.value = this.name;
        this._setInputSize(this.name);
        await this.model.root.update({
            'name': this.name,
        });
        super.discard();
    }

    /**
     * @private
     * @param {string} text in the input element
     */
    _setInputSize(text) {
        const { fontFamily, fontSize } = window.getComputedStyle(this.input.el);
        const font = `${fontSize} ${fontFamily}`;
        this.state_todo.inputSize =
            this._computeTextWidth(text || this.placeholder, font) +
            PADDING_RIGHT +
            PADDING_LEFT;
    }

    /**
     * Return the width in pixels of a text with the given font.
     * @private
     * @param {string} text
     * @param {string} font css font attribute value
     * @returns {number} width in pixels
     */
    _computeTextWidth(text, font) {
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");
        context.font = font;
        const width = context.measureText(text).width;
        // add a small extra margin, otherwise the text jitters in
        // the input because it overflows very slightly for some
        // letters (?).
        return Math.ceil(width) + WIDTH_MARGIN;
    }

    /**
     * Check if the name is empty or is the generic name
     * for untitled spreadsheets.
     * @param {string} name
     * @returns {boolean}
     */
    _isUntitled(name) {
        if (!name) {
            return true;
        }
        name = name.trim();
        return !name || name === UNTITLED_TODO_NAME.toString();
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onFocus(ev) {
        if (this._isUntitled(ev.target.value)) {
            ev.target.value = this.placeholder;
            ev.target.select();
        }
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onInput(ev) {
        const value = ev.target.value;
        this.state_todo.isUntitled = this._isUntitled(value);
        this.name = value;
        this._setInputSize(value);
        this.field_input.value = value;
        this.not_reload_name = true; //Do not reload the name of the record to not override the changes made by the user in the input
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onNameChanged(ev) {
        const value = ev.target.value.trim();
        ev.target.value = value;
        this._setInputSize(value);
        this.model.root.update({
            name: value,
        });
        this.not_reload_name = true;
        ev.target.blur();
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    async _onDoneToggled(ev) {
        this.saveButtonClicked();
        this.isDone = !this.isDone;
        //TODO: + orm call to update model state field
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _actualizeDoneState(ev) {
        this.state_todo.isDone = this.isDone;
    }
}

TodoFormController.template = 'note.TodoFormView';
