/** @odoo-module **/

import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";

import { Component, onMounted, useState, useRef, onWillUpdateProps } from "@odoo/owl";

const WIDTH_MARGIN = 3;
const PADDING_RIGHT = 5;
const PADDING_LEFT = PADDING_RIGHT - WIDTH_MARGIN;

export class SpreadsheetName extends Component {
    setup() {
        this.placeholder = UNTITLED_SPREADSHEET_NAME;
        this.state = useState({
            inputSize: 1,
            isUntitled: this._isUntitled(this.props.name),
            name: this.props.name,
        });
        this.input = useRef("speadsheetNameInput");

        onMounted(() => {
            this._setInputSize(this.state.name);
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.name !== this.props.name) {
                this.state.name = nextProps.name;
                this.state.isUntitled = this._isUntitled(nextProps.name);
            }
        });
    }

    /**
     * @private
     * @param {string} text in the input element
     */
    _setInputSize(text) {
        const { fontFamily, fontSize } = window.getComputedStyle(this.input.el);
        const font = `${fontSize} ${fontFamily}`;
        this.state.inputSize =
            this._computeTextWidth(text || this.placeholder, font) + PADDING_RIGHT + PADDING_LEFT;
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
        name = name.trim();
        return !name || name === UNTITLED_SPREADSHEET_NAME.toString();
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
        this.state.isUntitled = this._isUntitled(value);
        this.state.name = value;
        this._setInputSize(value);
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onNameChanged(ev) {
        const value = ev.target.value.trim();
        this.state.name = value || this.props.name;
        this._setInputSize(this.state.name);
        this.props.onSpreadsheetNameChanged({
            name: this.state.name,
        });
        ev.target.blur();
    }
}

SpreadsheetName.template = "spreadsheet_edition.SpreadsheetName";
SpreadsheetName.props = {
    name: String,
    isReadonly: Boolean,
    onSpreadsheetNameChanged: { type: Function, optional: true },
};
SpreadsheetName.defaultProps = {
    onSpreadsheetNameChanged: () => {},
};
