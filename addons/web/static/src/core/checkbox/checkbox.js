import { useHotkey } from "../hotkeys/hotkey_hook";

import { Component, props, signal, t } from "@odoo/owl";

/**
 * Custom checkbox
 *
 * <CheckBox
 *    value="boolean"
 *    disabled="boolean"
 *    onChange="_onValueChange"
 * >
 *    Change the label text
 * </CheckBox>
 *
 * @extends Component
 */

export class CheckBox extends Component {
    static template = "web.CheckBox";
    static nextId = 1;
    props = props({
        id: t.any().optional(),
        disabled: t.boolean().optional(),
        value: t.boolean().optional(),
        slots: t.object().optional(),
        onChange: t.function().optional(() => () => {}),
        className: t.string().optional(),
        name: t.string().optional(),
        indeterminate: t.boolean().optional(),
    });

    rootRef = signal(null);

    setup() {
        this.id = `checkbox-comp-${CheckBox.nextId++}`;

        // Make it toggleable through the Enter hotkey
        // when the focus is inside the root element
        useHotkey(
            "Enter",
            ({ area }) => {
                const oldValue = area.querySelector("input").checked;
                this.props.onChange(!oldValue);
            },
            { area: () => this.rootRef(), bypassEditableProtection: true }
        );
    }

    onClick(ev) {
        if (ev.composedPath().find((el) => ["INPUT", "LABEL"].includes(el.tagName))) {
            // The onChange will handle these cases.
            ev.stopPropagation();
            return;
        }

        // Reproduce the click event behavior as if it comes from the input element.
        const input = this.rootRef().querySelector("input");
        input.focus();
        if (!this.props.disabled) {
            ev.stopPropagation();
            input.checked = !input.checked;
            this.props.onChange(input.checked);
        }
    }

    onChange(ev) {
        if (!this.props.disabled) {
            this.props.onChange(ev.target.checked);
        }
    }
}
