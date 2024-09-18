import { registry } from "@web/core/registry";
import { PartnerAutoCompleteCharField, partnerAutoCompleteCharField } from "@partner_autocomplete/js/partner_autocomplete_fieldchar";
import { _t } from "@web/core/l10n/translation";
import { charWithPlaceholderField, CharWithPlaceholderField} from "./char_with_placeholder_field";

export class CharWithPlaceholderFieldAutoCompleteField extends PartnerAutoCompleteCharField {
    static template = "account.CharWithPlaceholderAutoCompleteField";
    static props = {
        ...PartnerAutoCompleteCharField.props,
        ...CharWithPlaceholderField.props,
    };

    static components = {
        ...PartnerAutoCompleteCharField.components,
    };

    /** Override **/
    get formattedValue() {
        return super.formattedValue || this.placeholder;
    }

    get placeholder() {
        return this.props.record.data[this.props.placeholderField] || this.props.placeholder;
    }
}

export const charWithPlaceholderFieldAutoCompleteField = {
    ...partnerAutoCompleteCharField,
    component: CharWithPlaceholderFieldAutoCompleteField,
    supportedOptions: [
        ...partnerAutoCompleteCharField.supportedOptions,
        ...charWithPlaceholderField.supportedOptions,
    ],
    extractProps: ({ attrs, options }) => ({
        ...partnerAutoCompleteCharField.extractProps({ attrs, options }),
        ...charWithPlaceholderField.extractProps({ attrs, options }),
    }),
};

registry.category("fields").add("char_with_placeholder_autocomplete_field", charWithPlaceholderFieldAutoCompleteField);
