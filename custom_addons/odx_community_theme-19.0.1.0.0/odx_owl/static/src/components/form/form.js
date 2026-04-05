/** @odoo-module **/

import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { nextId } from "@odx_owl/core/utils/ids";

function hasOwn(source, key) {
    return Boolean(source) && Object.prototype.hasOwnProperty.call(source, key);
}

function normalizeError(error) {
    if (!error) {
        return "";
    }
    if (typeof error === "object" && "message" in error) {
        return String(error.message || "");
    }
    return String(error);
}

function resolveFieldFlag(source, name) {
    if (!source || !name) {
        return false;
    }
    if (Array.isArray(source)) {
        return source.includes(name);
    }
    if (typeof source === "object") {
        return Boolean(source[name]);
    }
    return false;
}

export function getFormFieldContext(component) {
    const fieldContext = component.env.odxFormField;
    const itemContext = component.env.odxFormItem;

    if (!fieldContext) {
        throw new Error("odx_owl form components must be used inside <FormField>.");
    }
    if (!itemContext) {
        throw new Error("odx_owl form components must be used inside <FormItem>.");
    }

    const error = normalizeError(fieldContext.error);
    const describedByIds = [itemContext.descriptionId];
    if (error) {
        describedByIds.push(itemContext.messageId);
    }

    return {
        description: fieldContext.description || "",
        describedBy: describedByIds.filter(Boolean).join(" ") || undefined,
        disabled: Boolean(fieldContext.disabled),
        error,
        formDescriptionId: itemContext.descriptionId,
        formItemId: itemContext.formItemId,
        formMessageId: itemContext.messageId,
        id: itemContext.id,
        name: fieldContext.name,
        required: Boolean(fieldContext.required),
    };
}

export class Form extends Component {
    static template = "odx_owl.Form";
    static props = {
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        descriptions: { type: Object, optional: true },
        disabled: { type: Boolean, optional: true },
        disabledFields: { optional: true, validate: (v) => v == null || typeof v === "object" },
        errors: { type: Object, optional: true },
        id: { type: String, optional: true },
        noValidate: { type: Boolean, optional: true },
        onSubmit: { type: Function, optional: true },
        requiredFields: { optional: true, validate: (v) => v == null || typeof v === "object" },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        descriptions: {},
        disabled: false,
        errors: {},
        noValidate: true,
        tag: "form",
    };

    setup() {
        const self = this;
        useChildSubEnv({
            odxForm: {
                get disabled() {
                    return self.props.disabled;
                },
                getFieldDescription(name) {
                    if (!name || !hasOwn(self.props.descriptions, name)) {
                        return "";
                    }
                    return String(self.props.descriptions[name] || "");
                },
                getFieldError(name) {
                    if (!name || !hasOwn(self.props.errors, name)) {
                        return "";
                    }
                    return normalizeError(self.props.errors[name]);
                },
                isFieldDisabled(name) {
                    return self.props.disabled || resolveFieldFlag(self.props.disabledFields, name);
                },
                isFieldRequired(name) {
                    return resolveFieldFlag(self.props.requiredFields, name);
                },
            },
        });
    }

    get classes() {
        return cn("odx-form", this.props.className);
    }

    submit(ev) {
        if (this.props.noValidate) {
            ev.preventDefault();
        }
        this.props.onSubmit?.(ev);
    }
}

export class FormField extends Component {
    static template = "odx_owl.FormField";
    static props = {
        description: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        error: { optional: true, validate: (v) => v == null || typeof v === "string" || typeof v === "boolean" },
        name: { type: String },
        required: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        const self = this;
        useChildSubEnv({
            odxFormField: {
                get description() {
                    return self.descriptionText;
                },
                get disabled() {
                    return self.isDisabled;
                },
                get error() {
                    return self.errorText;
                },
                get name() {
                    return self.props.name;
                },
                get required() {
                    return self.isRequired;
                },
            },
        });
    }

    get descriptionText() {
        if (this.props.description !== undefined) {
            return this.props.description || "";
        }
        return this.env.odxForm?.getFieldDescription(this.props.name) || "";
    }

    get errorText() {
        if (this.props.error !== undefined) {
            return normalizeError(this.props.error);
        }
        return this.env.odxForm?.getFieldError(this.props.name) || "";
    }

    get isDisabled() {
        if (this.props.disabled !== undefined) {
            return this.props.disabled;
        }
        return Boolean(this.env.odxForm?.isFieldDisabled(this.props.name));
    }

    get isRequired() {
        if (this.props.required !== undefined) {
            return this.props.required;
        }
        return Boolean(this.env.odxForm?.isFieldRequired(this.props.name));
    }

    get slotProps() {
        return {
            description: this.descriptionText,
            disabled: this.isDisabled,
            error: this.errorText,
            name: this.props.name,
            required: this.isRequired,
        };
    }
}

export class FormItem extends Component {
    static template = "odx_owl.FormItem";
    static props = {
        className: { type: String, optional: true },
        id: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    setup() {
        const self = this;
        this.state = useState({
            id: nextId("odx-form-item"),
        });

        useChildSubEnv({
            odxFormItem: {
                get descriptionId() {
                    return `${self.itemId}-description`;
                },
                get formItemId() {
                    return `${self.itemId}-control`;
                },
                get id() {
                    return self.itemId;
                },
                get messageId() {
                    return `${self.itemId}-message`;
                },
            },
        });
    }

    get classes() {
        return cn("odx-form__item", this.props.className);
    }

    get itemId() {
        return this.props.id || this.state.id;
    }
}

export class FormLabel extends Component {
    static template = "odx_owl.FormLabel";
    static props = {
        className: { type: String, optional: true },
        forId: { type: String, optional: true },
        showRequiredIndicator: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
    };

    get classes() {
        return cn(
            "odx-form__label",
            {
                "odx-form__label--disabled": this.fieldContext.disabled,
                "odx-form__label--error": Boolean(this.fieldContext.error),
            },
            this.props.className
        );
    }

    get fieldContext() {
        return getFormFieldContext(this);
    }

    get labelForId() {
        return this.props.forId || this.fieldContext.formItemId;
    }

    get showRequiredIndicator() {
        const allowIndicator = this.props.showRequiredIndicator ?? true;
        return Boolean(allowIndicator && this.fieldContext.required);
    }
}

export class FormControl extends Component {
    static template = "odx_owl.FormControl";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    get classes() {
        return cn("odx-form__control", this.props.className);
    }

    get fieldContext() {
        return getFormFieldContext(this);
    }

    get slotProps() {
        const attrs = {
            "aria-describedby": this.fieldContext.describedBy,
            "aria-invalid": this.fieldContext.error ? "true" : undefined,
            "data-field-name": this.fieldContext.name || undefined,
            disabled: this.fieldContext.disabled ? true : undefined,
            id: this.fieldContext.formItemId,
            name: this.fieldContext.name || undefined,
            required: this.fieldContext.required ? true : undefined,
        };

        return {
            ...this.fieldContext,
            attrs,
        };
    }
}

export class FormDescription extends Component {
    static template = "odx_owl.FormDescription";
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

    get classes() {
        return cn("odx-form__description", this.props.className);
    }

    get contentText() {
        return this.props.text || this.fieldContext.description || "";
    }

    get descriptionId() {
        return getFormFieldContext(this).formDescriptionId;
    }

    get fieldContext() {
        return getFormFieldContext(this);
    }

    get hasContent() {
        return Boolean(this.contentText || this.props.slots?.default);
    }
}

export class FormMessage extends Component {
    static template = "odx_owl.FormMessage";
    static props = {
        className: { type: String, optional: true },
        forceMount: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        forceMount: false,
        tag: "p",
        text: "",
    };

    get classes() {
        return cn("odx-form__message", this.props.className);
    }

    get fieldContext() {
        return getFormFieldContext(this);
    }

    get hasContent() {
        return Boolean(this.messageText || this.props.slots?.default || this.props.forceMount);
    }

    get isErrorMessage() {
        return Boolean(this.fieldContext.error);
    }

    get messageId() {
        return this.fieldContext.formMessageId;
    }

    get messageText() {
        return this.fieldContext.error || this.props.text || "";
    }
}
