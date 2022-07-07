/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { archParseBoolean } from "@web/views/utils";
import { formatChar } from "../formatters";
import { useInputField } from "../input_field_hook";
import { standardFieldProps } from "../standard_field_props";
import { TranslationButton } from "../translation_button";

const { Component } = owl;

export class CharField extends Component {
    setup() {
        useInputField({ getValue: () => this.props.value || "", parse: (v) => this.parse(v) });
    }

    get formattedValue() {
        return formatChar(this.props.value, { isPassword: this.props.isPassword });
    }

    parse(value) {
        if (this.props.shouldTrim) {
            return value.trim();
        }
        return value;
    }
}

CharField.template = "web.CharField";
CharField.components = {
    TranslationButton,
};
CharField.props = {
    ...standardFieldProps,
    autocomplete: { type: String, optional: true },
    isPassword: { type: Boolean, optional: true },
    placeholder: { type: String, optional: true },
    shouldTrim: { type: Boolean, optional: true },
    maxLength: { type: Number, optional: true },
    isTranslatable: { type: Boolean, optional: true },
    resId: { type: [Number, Boolean], optional: true },
    resModel: { type: String, optional: true },
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
        isPassword: archParseBoolean(attrs.password),
        placeholder: attrs.placeholder,
    };
};

registry.category("fields").add("char", CharField);
