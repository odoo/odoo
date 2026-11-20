import { Component, proxy, signal, t, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useAutofocus } from "@web/core/utils/hooks";

export class SubtaskCreate extends Component {
    static template = "project.SubtaskCreate";
    props = useProps({
        onSubtaskCreateNameChanged: t.function(),
        onClose: t.function(),
    });

    root = signal.ref();
    input = signal.ref();

    setup() {
        this.placeholder = _t("Write a task name");
        this.state = proxy({
            name: "",
            isFieldInvalid: false,
        });
        useAutofocus({ ref: this.input });
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
     * @param {KeyboardEvent} ev
     */
    _onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.onClose();
        }
    }

    /**
     * Close the input when it loses the focus while empty, unless the focus
     * goes to the "Add" button (which shows the empty name error instead).
     * A non-empty name is created by the `change` event, not here.
     *
     * @private
     * @param {FocusEvent} ev
     */
    _onBlur(ev) {
        if (ev.target.value.trim() === "" && !this.root()?.contains(ev.relatedTarget)) {
            this.props.onClose();
        }
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
