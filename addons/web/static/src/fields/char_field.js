/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { TranslationButton } from "./translation_button";

const { Component, useComponent, useEffect, useRef } = owl;

function useInputField(refName = "input") {
    const component = useComponent();
    const inputRef = useRef(refName);
    let isDirty = false;
    let lastSetValue = null;
    function onInput(ev) {
        isDirty = ev.target.value !== lastSetValue;
    }
    function onChange(ev) {
        lastSetValue = ev.target.value;
        isDirty = false;
    }
    useEffect(
        (inputEl) => {
            if (inputEl) {
                inputEl.addEventListener("input", onInput);
                inputEl.addEventListener("change", onChange);
                return () => {
                    inputEl.removeEventListener("input", onInput);
                    inputEl.removeEventListener("change", onChange);
                };
            }
        },
        () => [inputRef.el]
    );
    useEffect(() => {
        if (inputRef.el && !isDirty) {
            inputRef.el.value = component.props.value || "";
            lastSetValue = inputRef.el.value;
        }
    });
}

export class CharField extends Component {
    setup() {
        useInputField();
    }

    get formattedValue() {
        let value = typeof this.props.value === "string" ? this.props.value : "";
        if (this.props.isPassword) {
            value = "*".repeat(value.length);
        }
        return value;
    }

    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let value = ev.target.value;
        if (this.props.shouldTrim) {
            value = value.trim();
        }
        this.props.update(value || false);
    }
}

CharField.template = "web.CharField";
CharField.props = {
    ...standardFieldProps,
    autocomplete: { type: String, optional: true },
    isPassword: { type: Boolean, optional: true },
    placeholder: { type: String, optional: true },
    shouldTrim: { type: Boolean, optional: true },
    maxLength: { type: Number, optional: true },
    isTranslatable: { type: Boolean, optional: true },
    resId: { type: Number | Boolean, optional: true },
    resModel: { type: String, optional: true },
};
CharField.components = {
    TranslationButton,
};
CharField.displayName = _lt("Text");
CharField.supportedTypes = ["char"];
CharField.extractProps = (fieldName, record, attrs) => {
    return {
        shouldTrim: record.fields[fieldName].trim,
        maxLength: record.fields[fieldName].size,
        isTranslatable: record.fields[fieldName].translate,
        resId: record.resId,
        resModel: record.resModel,

        autocomplete: attrs.autocomplete,
        isPassword: Boolean(attrs.password && !/^(0|false)$/i.test(attrs.password)),
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("char", CharField);
