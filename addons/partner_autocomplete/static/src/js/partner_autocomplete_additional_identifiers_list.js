import { useChildRef, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { AdditionalIdentifiersList, additionalIdentifiersList } from "@web/views/fields/additional_identifiers/additional_identifiers";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class PartnerAutoCompleteAdditionalIdentifiersList extends AdditionalIdentifiersList {
    static template = "partner_autocomplete.PartnerAutoCompleteAdditionalIdentifiersList";
    static components = {
        ...AdditionalIdentifiersList.components,
        AutoComplete,
    };
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.partnerAutocomplete = usePartnerAutocomplete();

        this.inputRef = useChildRef();
    }

    async getSearchConfig(request, identifierName, shouldSearchWorldWide) {
        let defaultCountryId = this.props.record.data?.country_id?.id || false;
        if (shouldSearchWorldWide) {
            defaultCountryId = 0;
        }

        const rules = {
            'DUNS': {
                isValid: request && request.length === 9,
                countryId: 0
            },
            'BE_EN': {
                isValid: request && request.length >= 10,
                countryId: defaultCountryId
            },
            'FR_SIRET': {
                isValid: request && request.length >= 14,
                countryId: defaultCountryId
            },
            'FR_SIREN': {
                isValid: request && request.length >= 9,
                countryId: defaultCountryId
            },
        };

        if (rules[identifierName]) {
            return rules[identifierName];
        }

        return {
            isValid: await this.validateSearchTerm(request),
            countryId: defaultCountryId
        };
    }

    async validateSearchTerm(request) {
        return request && request.length > 2;
    }

    getSources(identifierName) {
        return [
            {
                options: async (request, shouldSearchWorldWide) => {
                    const config = await this.getSearchConfig(request, identifierName, shouldSearchWorldWide);
                    if (!config.isValid) {
                        return [];
                    }
                    const suggestions = await this.partnerAutocomplete.autocomplete(request, config.country_id, identifierName);
                    return suggestions.map((suggestion) => ({
                        cssClass: "partner_autocomplete_dropdown_char",
                        data: suggestion,
                        label: suggestion.name,
                        onSelect: () => this.onSelectPartnerAutocompleteOption(suggestion),
                    }));
                },
                optionSlot: "partnerOption",
                placeholder: _t('Searching Autocomplete...'),
            },
        ];
    }

    async onSelectPartnerAutocompleteOption(option) {
        let data = await this.partnerAutocomplete.getCreateData(option);
        if (!data?.company) {
            return;
        }

        if (data.logo) {
            const logoField = this.props.record.resModel === 'res.partner' ? 'image_1920' : 'logo';
            data.company[logoField] = data.logo;
        }

        const additionalData = {
            entity_type: data.company.entity_type,
            unspsc_codes: data.company.unspsc_codes,
        };
        // Delete useless fields before updating record
        data.company = this.partnerAutocomplete.removeUselessFields(data.company, Object.keys(this.props.record.fields));

        // Update record with retrieved values
        if (data.company.name) {
            await this.props.record.update({ name: data.company.name });  // Needed otherwise name it is not saved
        }
        await this.props.record.update(data.company);

        // Post message with company info card
        if (this.props.record.resModel === 'res.partner') {
            const saved = await this.props.record.save();
            if (saved && data.isEnrichAccessible) {
                await this.orm.call("res.partner", "enrich_company_message_post", [this.props.record.resId, additionalData]);
                this.props.record.load();
            }
        }
    }
}

export const partnerAutoCompleteAdditionalIdentifiersList = {
    ...additionalIdentifiersList,
    component: PartnerAutoCompleteAdditionalIdentifiersList,
};

registry.category("fields").add("additional_identifiers_list_partner_autocomplete", partnerAutoCompleteAdditionalIdentifiersList);
