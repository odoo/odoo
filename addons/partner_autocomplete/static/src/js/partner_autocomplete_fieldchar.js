/** @odoo-module **/
/* global checkVATNumber */

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useChildRef } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";
import { loadJS } from "@web/core/assets";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core"

export class PartnerAutoCompleteCharField extends CharField {
    setup() {
        super.setup();

        this.partner_autocomplete = usePartnerAutocomplete();

        this.inputRef = useChildRef();
        useInputField({ getValue: () => this.props.value || "", parse: (v) => this.parse(v), ref: this.inputRef});
    }

    sanitizeVAT(request) {
        return request ? request.replace(/[^A-Za-z0-9]/g, '') : '';
    }

    isVAT(request) {
        // checkVATNumber is defined in library jsvat.
        // It validates that the input has a valid VAT number format
        return checkVATNumber(this.sanitizeVAT(request));
    }

    validateSearchTerm(request) {
        if (this.props.name == 'vat') {
            return this.isVAT(request);
        }
        else {
            return request && request.length > 2;
        }
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    // Lazyload jsvat only if the component is being used.
                    await loadJS("/partner_autocomplete/static/lib/jsvat.js");
                    
                    if (this.validateSearchTerm(request)) {
                        const suggestions = await this.partner_autocomplete.autocomplete(request, this.isVAT(request));
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

registry.category("fields").add("field_partner_autocomplete", PartnerAutoCompleteCharField);
