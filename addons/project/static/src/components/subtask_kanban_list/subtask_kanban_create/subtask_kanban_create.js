import { Component, proxy, signal } from "@odoo/owl";

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

    input = signal(null);

    setup() {
        this.placeholder = _t("Write a task name");
        this.state = proxy({
            inputSize: 1,
            name: this.props.name,
            isFieldInvalid: false,
        });
        useAutofocus({ ref: this.input });
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
        this.state.isFieldInvalid = false;
    }

    _onClick() {
        this.input()?.focus();
    }

    /**
     * @private
     * @param {InputEvent} ev
     */
    _onNameChanged(ev) {
        const value = ev.target.value.trim();
        if (value !== "") {
            this.props.onSubtaskCreateNameChanged(value);
            ev.target.blur();
        }
    }

    _onSaveClick() {
        if (this.input().value.trim() === "") {
            this.props.onSubtaskCreateNameChanged(this.input().value.trim());
            this.state.isFieldInvalid = true;
            this.state.name = "";
        }
    }
}
