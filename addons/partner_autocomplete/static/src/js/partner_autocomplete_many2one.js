/** @odoo-module **/

import { Many2XAutocomplete } from '@web/views/fields/relational_utils';
import { Many2OneField, many2OneField } from '@web/views/fields/many2one/many2one_field';
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core"

export class PartnerMany2XAutocomplete extends Many2XAutocomplete {
    setup() {
        super.setup();
        this.partner_autocomplete = usePartnerAutocomplete();
    }

    validateSearchTerm(request) {
        return request && request.length > 2;
    }

    get sources() {
        return super.sources.concat(
            {
                options: async (request) => {
                    if (this.validateSearchTerm(request)) {
                        const suggestions = await this.partner_autocomplete.autocomplete(request);
                        suggestions.forEach((suggestion) => {
                            suggestion.classList = "partner_autocomplete_dropdown_many2one";
                            suggestion.isFromPartnerAutocomplete = true;
                        });
                        return suggestions;
                    }
                    else {
                        return [];
                    }
                },
                optionTemplate: "partner_autocomplete.Many2oneDropdownOption",
                placeholder: _t('Searching Autocomplete...'),
            },
        );
    }

    async onSelect(option, params) {
        if (option.isFromPartnerAutocomplete) {  // Checks that it is a partner autocomplete option
            const data = await this.partner_autocomplete.getCreateData(Object.getPrototypeOf(option));
            let context = {
                'default_is_company': true
            };

            for (const [key, val] of Object.entries(data.company)) {
                context['default_' + key] = val && val.id ? val.id : val;
            }

            if (data.logo) {
                context.default_image_1920 = data.logo;
            }
            return this.openMany2X({ context });
        }
        else {
            return super.onSelect(option, params);
        }
    }

}

export class PartnerAutoCompleteMany2one extends Many2OneField {}

PartnerAutoCompleteMany2one.components = {
    ...Many2OneField.components,
    Many2XAutocomplete: PartnerMany2XAutocomplete,
}

export const partnerAutoCompleteMany2one = {
    ...many2OneField,
    component: PartnerAutoCompleteMany2one,
};

registry.category("fields").add("res_partner_many2one", partnerAutoCompleteMany2one);
