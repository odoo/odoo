/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { cva } from "@odx_owl/core/utils/variants";

export const toggleVariants = cva("odx-toggle", {
    variants: {
        variant: {
            default: "odx-toggle--default",
            outline: "odx-toggle--outline",
        },
        size: {
            default: "odx-toggle--size-default",
            sm: "odx-toggle--size-sm",
            lg: "odx-toggle--size-lg",
        },
    },
    defaultVariants: {
        variant: "default",
        size: "default",
    },
});

export class Toggle extends Component {
    static template = "odx_owl.Toggle";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        defaultPressed: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        name: { type: String, optional: true },
        onPressedChange: { type: Function, optional: true },
        pressed: { type: Boolean, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        defaultPressed: false,
        disabled: false,
        size: "default",
        value: "on",
        variant: "default",
    };

    setup() {
        this.state = useState({
            pressed: this.props.pressed ?? this.props.defaultPressed,
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.pressed !== undefined) {
                this.state.pressed = nextProps.pressed;
            }
        });
    }

    get isPressed() {
        return this.props.pressed ?? this.state.pressed;
    }

    get classes() {
        return toggleVariants({
            variant: this.props.variant,
            size: this.props.size,
            className: this.props.className,
        });
    }

    toggle(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            return;
        }
        const next = !this.isPressed;
        if (this.props.pressed === undefined) {
            this.state.pressed = next;
        }
        this.props.onPressedChange?.(next);
    }
}
