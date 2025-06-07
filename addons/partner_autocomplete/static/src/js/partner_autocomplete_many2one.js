/** @odoo-module **/

import { Many2XAutocomplete } from '@web/views/fields/relational_utils';
import { Many2OneField, many2OneField } from '@web/views/fields/many2one/many2one_field';
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core";
import { PartnerAutoComplete } from "@partner_autocomplete/js/partner_autocomplete_component";

export class PartnerMany2XAutocomplete extends Many2XAutocomplete {
    static template = "partner_autocomplete.PartnerAutoCompleteMany2XField";
    static components = {
        ...Many2XAutocomplete.components,
        PartnerAutoComplete,
    };

    setup() {
        super.setup();
        this.partnerAutocomplete = usePartnerAutocomplete();
    }

    validateSearchTerm(request) {
        return request && request.length > 2;
    }

    get sources() {
        const sources = super.sources;
        if (!this.props.canCreate) {
            return sources;
        }
        return sources.concat(
            {
                options: async (request, shouldSearchWorldWide) => {
                    if (this.validateSearchTerm(request)) {
                        let queryCountryId = false;
                        if (shouldSearchWorldWide){
                            queryCountryId = 0;
                        }
                        const suggestions = await this.partnerAutocomplete.autocomplete(request, queryCountryId);
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
                optionTemplate: "partner_autocomplete.DropdownOption",
                placeholder: _t("Searching Autocomplete..."),
            },
        );
    }

    async onSelect(option, params) {
        if (option.isFromPartnerAutocomplete) {  // Checks that it is a partner autocomplete option
            const data = await this.partnerAutocomplete.getCreateData(Object.getPrototypeOf(option));
            if (!data?.company) {
                return;
            }
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

PartnerMany2XAutocomplete.props = {
    ...Many2XAutocomplete.props,
    canCreate: { type: Boolean, optional: true },
}

export class PartnerAutoCompleteMany2one extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: PartnerMany2XAutocomplete,
    };
    static props = {
        ...Many2OneField.props,
        canCreate: this.props.canCreate,
    };
    get Many2XAutocompleteProps() {
        return {
            ...super.Many2XAutocompleteProps,
            canCreate: this.props.canCreate,
        };
    }
}

export const partnerAutoCompleteMany2one = {
    ...many2OneField,
    component: PartnerAutoCompleteMany2one,
};

registry.category("fields").add("res_partner_many2one", partnerAutoCompleteMany2one);
