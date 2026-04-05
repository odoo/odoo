/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { cva } from "@odx_owl/core/utils/variants";

export const fieldVariants = cva("odx-field", {
    variants: {
        orientation: {
            vertical: "odx-field--vertical",
            horizontal: "odx-field--horizontal",
            responsive: "odx-field--responsive",
        },
    },
    defaultVariants: {
        orientation: "vertical",
    },
});

class FieldBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class FieldSet extends FieldBase {
    static template = "odx_owl.FieldSet";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        invalid: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        invalid: false,
    };
    baseClass = "odx-field-set";
}

export class FieldLegend extends Component {
    static template = "odx_owl.FieldLegend";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
        variant: "legend",
    };

    get classes() {
        return cn(
            "odx-field-legend",
            `odx-field-legend--${this.props.variant}`,
            this.props.className
        );
    }
}

export class FieldGroup extends FieldBase {
    static template = "odx_owl.FieldGroup";
    static props = {
        className: { type: String, optional: true },
        variant: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
        variant: "default",
    };
    baseClass = "odx-field-group";
}

export class Field extends Component {
    static template = "odx_owl.Field";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        invalid: { type: Boolean, optional: true },
        orientation: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        invalid: false,
        orientation: "vertical",
        tag: "div",
    };

    get classes() {
        return fieldVariants({
            orientation: this.props.orientation,
            className: this.props.className,
        });
    }
}

export class FieldContent extends FieldBase {
    static template = "odx_owl.FieldContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-field-content";
}

export class FieldLabel extends Component {
    static template = "odx_owl.FieldLabel";
    static props = {
        className: { type: String, optional: true },
        forId: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
    };

    get classes() {
        return cn("odx-field-label", this.props.className);
    }
}

export class FieldTitle extends FieldBase {
    static template = "odx_owl.FieldTitle";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
        text: "",
    };
    baseClass = "odx-field-title";
}

export class FieldDescription extends FieldBase {
    static template = "odx_owl.FieldDescription";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "p",
        text: "",
    };
    baseClass = "odx-field-description";
}

export class FieldSeparator extends Component {
    static template = "odx_owl.FieldSeparator";
    static props = {
        className: { type: String, optional: true },
        content: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        content: "",
    };

    get classes() {
        return cn("odx-field-separator", this.props.className);
    }

    get hasContent() {
        return Boolean(this.props.content || this.props.slots?.default);
    }
}

export class FieldError extends Component {
    static template = "odx_owl.FieldError";
    static props = {
        className: { type: String, optional: true },
        errors: { type: Array, optional: true },
        forceMount: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        errors: [],
        forceMount: false,
        text: "",
    };

    get classes() {
        return cn("odx-field-error", this.props.className);
    }

    get errorMessages() {
        const messages = [];
        if (this.props.text) {
            messages.push(this.props.text);
        }
        for (const error of this.props.errors || []) {
            if (!error) {
                continue;
            }
            const message = typeof error === "object" && "message" in error
                ? error.message
                : error;
            if (message && !messages.includes(String(message))) {
                messages.push(String(message));
            }
        }
        return messages;
    }

    get hasContent() {
        return Boolean(this.errorMessages.length || this.props.slots?.default || this.props.forceMount);
    }
}
