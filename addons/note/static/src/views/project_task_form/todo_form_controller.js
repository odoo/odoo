/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";
const { Component, onMounted, onRendered, onWillStart, useState, useRef, onWillUpdateProps } = owl;

const UNTITLED_TODO_NAME = _lt("Untitled to-do");
const WIDTH_MARGIN = 3;
const PADDING_RIGHT = 5;
const PADDING_LEFT = PADDING_RIGHT - WIDTH_MARGIN;

/** The FormController is overrided to be able to manage the edition of the name of a to-do directly
 *  in the breadcrumb. As:
 *      - this edition needs to interact with the status buttons (save/discard, available at controller
 *        level)
 *      - the record is not available at controller loading (therefore no solution to use a Field
 *        component to edit the name has been found)
 *  the editable name "component" is directly implemented at controller level. This is not ideal as
 *  changes in the state values are not managed to re-render the component. Therefore, update of the
 *  input value has to be done manually.
 *
 *  On top of that function related to the navigation in the control panel need to be rewritten
 *  manually (onPagerUpdate and create).
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
        });

        onMounted(() => {
            this.name = (this.model.root) ? this.model.root.data.display_name || "": "";
            this.state_todo.isUntitled = this._isUntitled(this.name);
            this.saved_name = this.name;

            this.field_input = document.getElementsByClassName("o_todo_breadcrumb_name_input")[0];
            this.field_input.value = this.name;
            this._setInputSize(this.name);
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
        ev.target.blur();
    }

    /**
     * Override from ControlPanel
     */
    async onPagerUpdate({ offset, resIds }) {
        await this.model.root.askChanges(); // ensures that isDirty is correct
        let canProceed = true;
        if (this.model.root.isDirty) {
            canProceed = await this.model.root.save({
                stayInEdition: true,
                useSaveErrorDialog: true,
            });
        }
        if (canProceed) {
            await this.model.load({ resId: resIds[offset] });
            this.name = (this.model.root) ? this.model.root.data.display_name || "": "";
            this.state_todo.isUntitled = this._isUntitled(this.name);
            this.saved_name = this.name;

            this.field_input.value = this.name;
            this._setInputSize(this.name);
            //return new_model;
        }
    }

    /**
     * Override from ControlPanel
     */
    async create() {
        await this.model.root.askChanges(); // ensures that isDirty is correct
        let canProceed = true;
        if (this.model.root.isDirty) {
            canProceed = await this.model.root.save({
                stayInEdition: true,
                useSaveErrorDialog: true,
            });
        }
        if (canProceed) {
            this.disableButtons();
            await this.model.load({ resId: null });
            
            this.name = "";
            this.state_todo.isUntitled = this._isUntitled(this.name);
            this.saved_name = this.name;

            this.field_input.value = this.name;
            this._setInputSize(this.name);

            this.enableButtons();
        }
    }
}

TodoFormController.template = 'note.TodoFormView';
