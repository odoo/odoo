/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useChildRef } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core"

export class PartnerAutoCompleteCharField extends CharField {
    setup() {
        super.setup();

        this.partner_autocomplete = usePartnerAutocomplete();

        this.inputRef = useChildRef();
        useInputField({ getValue: () => this.props.record.data[this.props.name] || "", parse: (v) => this.parse(v), ref: this.inputRef});
    }

    async validateSearchTerm(request) {
        if (this.props.name == 'vat') {
            return this.partner_autocomplete.isTAXNumber(request);
        }
        else {
            return request && request.length > 2;
        }
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    if (await this.validateSearchTerm(request)) {
                        const suggestions = await this.partner_autocomplete.autocomplete(request);
                        suggestions.forEach((suggestion) => {
                            suggestion.classList = "partner_autocomplete_dropdown_char";
                        });
                        return suggestions;
                    }
                    else {
                        return [];
                    }
                },
                optionTemplate: "partner_autocomplete.CharFieldDropdownOption",
                placeholder: _t('Searching Autocomplete...'),
            },
        ];
    }

    async onSelect(option) {
        const data = await this.partner_autocomplete.getCreateData(Object.getPrototypeOf(option));

        if (data.logo) {
            const logoField = this.props.record.resModel === 'res.partner' ? 'image_1920' : 'logo';
            data.company[logoField] = data.logo;
        }

        // Some fields are unnecessary in res.company
        if (this.props.record.resModel === 'res.company') {
            const fields = ['comment', 'child_ids', 'additional_info'];
            fields.forEach((field) => {
                delete data.company[field];
            });
        }

        // Format the many2one fields
        const many2oneFields = ['country_id', 'state_id'];
        many2oneFields.forEach((field) => {
            if (data.company[field]) {
                data.company[field] = [data.company[field].id, data.company[field].display_name];
            }
        });
        this.props.record.update(data.company);
    }
}

PartnerAutoCompleteCharField.template = "partner_autocomplete.PartnerAutoCompleteCharField";
PartnerAutoCompleteCharField.components = {
    ...CharField.components,
    AutoComplete,
};

export const partnerAutoCompleteCharField = {
    ...charField,
    component: PartnerAutoCompleteCharField,
};

registry.category("fields").add("field_partner_autocomplete", partnerAutoCompleteCharField);
