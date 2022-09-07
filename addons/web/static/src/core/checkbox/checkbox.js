/** @odoo-module **/

import { useHotkey } from "../hotkeys/hotkey_hook";

const { Component, useRef } = owl;

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
    setup() {
        this.id = `checkbox-comp-${CheckBox.nextId++}`;
        this.rootRef = useRef("root");

        // Make it toggleable through the Enter hotkey
        // when the focus is inside the root element
        useHotkey(
            "Enter",
            ({ area }) => {
                const oldValue = area.querySelector("input").checked;
                this.props.onChange(!oldValue);
            },
            { area: () => this.rootRef.el, bypassEditableProtection: true }
        );
    }

    onClick(ev) {
        if (ev.composedPath().find((el) => ["INPUT", "LABEL"].includes(el.tagName))) {
            // The onChange will handle these cases.
            ev.stopPropagation();
            return;
        }

        // Reproduce the click event behavior as if it comes from the input element.
        const input = this.rootRef.el.querySelector("input");
        input.focus();
        if (!this.props.disabled) {
            ev.stopPropagation();
            input.checked = !input.checked;
        }
        this.props.onChange(input.checked);
    }

    onChange(ev) {
        this.props.onChange(ev.target.checked);
    }
}

CheckBox.template = "web.CheckBox";
CheckBox.nextId = 1;
CheckBox.defaultProps = {
    onChange: () => {},
};
CheckBox.props = {
    id: {
        type: true,
        optional: true,
    },
    disabled: {
        type: Boolean,
        optional: true,
    },
    value: {
        type: Boolean,
        optional: true,
    },
    slots: {
        type: Object,
        optional: true,
    },
    onChange: {
        type: Function,
        optional: true,
    },
    className: {
        type: String,
        optional: true,
    },
    name: {
        type: String,
        optional: true,
    },
};
