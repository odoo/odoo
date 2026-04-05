/** @odoo-module **/

import { Component, useChildSubEnv } from "@odoo/owl";
import { Button, buttonVariants } from "@odx_owl/components/button/button";
import { Input } from "@odx_owl/components/input/input";
import { Textarea } from "@odx_owl/components/textarea/textarea";
import { cn } from "@odx_owl/core/utils/cn";
import { cva } from "@odx_owl/core/utils/variants";

export const inputGroupAddonVariants = cva("odx-input-group__addon", {
    variants: {
        align: {
            "inline-start": "odx-input-group__addon--inline-start",
            "inline-end": "odx-input-group__addon--inline-end",
            "block-start": "odx-input-group__addon--block-start",
            "block-end": "odx-input-group__addon--block-end",
        },
    },
    defaultVariants: {
        align: "inline-start",
    },
});

export const inputGroupButtonVariants = cva("odx-input-group__button", {
    variants: {
        size: {
            xs: "odx-input-group__button--xs",
            sm: "odx-input-group__button--sm",
            "icon-xs": "odx-input-group__button--icon-xs",
            "icon-sm": "odx-input-group__button--icon-sm",
        },
    },
    defaultVariants: {
        size: "xs",
    },
});

function getButtonBaseSize(size) {
    if (size === "sm" || size === "icon-sm") {
        return "sm";
    }
    return "sm";
}

export class InputGroup extends Component {
    static template = "odx_owl.InputGroup";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        tag: "div",
    };

    setup() {
        const self = this;
        useChildSubEnv({
            odxInputGroup: {
                get disabled() {
                    return self.props.disabled;
                },
            },
        });
    }

    get classes() {
        return cn("odx-input-group", this.props.className);
    }
}

export class InputGroupAddon extends Component {
    static template = "odx_owl.InputGroupAddon";
    static props = {
        align: { type: String, optional: true },
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        align: "inline-start",
        className: "",
        tag: "div",
    };

    get classes() {
        return inputGroupAddonVariants({
            align: this.props.align,
            className: this.props.className,
        });
    }

    focusControl(ev) {
        if (ev.target.closest("button")) {
            return;
        }
        ev.currentTarget.parentElement
            ?.querySelector('[data-slot="input-group-control"]')
            ?.focus();
    }
}

export class InputGroupButton extends Component {
    static template = "odx_owl.InputGroupButton";
    static components = {
        Button,
    };
    static props = Button.props;
    static defaultProps = {
        ...Button.defaultProps,
        size: "xs",
        variant: "ghost",
    };

    get classes() {
        return buttonVariants({
            variant: this.props.variant,
            size: getButtonBaseSize(this.props.size),
            className: inputGroupButtonVariants({
                size: this.props.size,
                className: this.props.className,
            }),
        });
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxInputGroup?.disabled;
    }
}

export class InputGroupText extends Component {
    static template = "odx_owl.InputGroupText";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "span",
        text: "",
    };

    get classes() {
        return cn("odx-input-group__text", this.props.className);
    }
}

export class InputGroupInput extends Component {
    static template = "odx_owl.InputGroupInput";
    static components = {
        Input,
    };
    static props = Input.props;
    static defaultProps = {
        ...Input.defaultProps,
        className: "",
    };

    get classes() {
        return cn("odx-input-group__control odx-input-group__input", this.props.className);
    }

    get mergedAttrs() {
        return {
            ...this.props.attrs,
            "data-slot": "input-group-control",
        };
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxInputGroup?.disabled;
    }
}

export class InputGroupTextarea extends Component {
    static template = "odx_owl.InputGroupTextarea";
    static components = {
        Textarea,
    };
    static props = Textarea.props;
    static defaultProps = {
        ...Textarea.defaultProps,
        className: "",
    };

    get classes() {
        return cn("odx-input-group__control odx-input-group__textarea", this.props.className);
    }

    get mergedAttrs() {
        return {
            ...this.props.attrs,
            "data-slot": "input-group-control",
        };
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxInputGroup?.disabled;
    }
}
