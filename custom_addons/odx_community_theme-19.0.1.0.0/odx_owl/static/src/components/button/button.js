/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cva } from "@odx_owl/core/utils/variants";

export const buttonVariants = cva("odx-button", {
    variants: {
        variant: {
            default: "odx-button--default",
            destructive: "odx-button--destructive",
            outline: "odx-button--outline",
            secondary: "odx-button--secondary",
            ghost: "odx-button--ghost",
            link: "odx-button--link",
        },
        size: {
            default: "odx-button--size-default",
            sm: "odx-button--size-sm",
            lg: "odx-button--size-lg",
            icon: "odx-button--size-icon",
        },
    },
    defaultVariants: {
        variant: "default",
        size: "default",
    },
});

export class Button extends Component {
    static template = "odx_owl.Button";
    static props = {
        attrs: { type: Object, optional: true },
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        href: { type: String, optional: true },
        label: { type: String, optional: true },
        loading: { type: Boolean, optional: true },
        name: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        rel: { type: String, optional: true },
        role: { type: String, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tabindex: { type: Number, optional: true },
        tag: { type: String, optional: true },
        target: { type: String, optional: true },
        title: { type: String, optional: true },
        type: { type: String, optional: true },
        value: { optional: true, validate: () => true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        disabled: false,
        loading: false,
        size: "default",
        tag: "button",
        type: "button",
        variant: "default",
    };

    get computedTag() {
        if (this.props.tag !== "button") {
            return this.props.tag;
        }
        return this.props.href ? "a" : "button";
    }

    get classes() {
        return buttonVariants({
            variant: this.props.variant,
            size: this.props.size,
            className: this.props.className,
        });
    }

    onClick(ev) {
        if (this.props.disabled || this.props.loading) {
            ev.preventDefault();
            ev.stopPropagation();
            return;
        }
        this.props.onClick?.(ev);
    }
}
