/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";
import { TranslationButton } from "./translation_button";

const { Component } = owl;

export class CharField extends Component {
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
