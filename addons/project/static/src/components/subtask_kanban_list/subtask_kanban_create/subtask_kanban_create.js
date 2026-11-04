/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";

export class SubtaskCreate extends Component {
    static template = "project.SubtaskCreate";
    static props = {
        name: String,
        isReadonly: { type: Boolean, optional: true },
        onSubtaskCreateNameChanged: { type: Function },
        onBlur: { type: Function },
    };
    setup() {
        this.placeholder = _t("Add Sub-tasks");
        this.state = useState({
            inputSize: 1,
            name: this.props.name,
        });
        this.input = useRef("subtaskCreateInput");
        useAutofocus({ refName: "subtaskCreateInput" });
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onFocus(ev) {
        ev.target.value = this.placeholder;
        ev.target.select();
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onInput(ev) {
        const value = ev.target.value;
        this.state.name = value;
    }

    _onClick() {
        this.input.el.focus();
    }

    async _onBlur() {
        this.props.onBlur();
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onNameChanged(ev) {
        const value = ev.target.value.trim();
        this.props.onSubtaskCreateNameChanged(value);
        ev.target.blur();
    }

    _onSaveClick() {
        if (this.input.el.value !== "") {
            this.props.onSubtaskCreateNameChanged(this.input.el.value);
        }
    }
}
