/** @odoo-module **/

import { useChildRef, useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core";
import { PartnerAutoComplete } from "@partner_autocomplete/js/partner_autocomplete_component";

export class PartnerAutoCompleteCharField extends CharField {
    static template = "partner_autocomplete.PartnerAutoCompleteCharField";
    static components = {
        ...CharField.components,
        PartnerAutoComplete,
    };
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.partnerAutocomplete = usePartnerAutocomplete();

        this.inputRef = useChildRef();
        useInputField({ getValue: () => this.props.record.data[this.props.name] || "", parse: (v) => this.parse(v), ref: this.inputRef});
    }

    async validateSearchTerm(request) {
        return request && request.length > 2;
    }

    get sources() {
        return [
            {
                options: async (request, shouldSearchWorldWide) => {
                    if (await this.validateSearchTerm(request)) {
                        let queryCountryId = this.props.record.data?.country_id ? this.props.record.data.country_id[0] : false;
                        if (shouldSearchWorldWide){
                            queryCountryId = 0;
                        }
                        const suggestions = await this.partnerAutocomplete.autocomplete(request, queryCountryId);
                        suggestions.forEach((suggestion) => {
                            suggestion.classList = "partner_autocomplete_dropdown_char";
                        });
                        return suggestions;
                    }
                    else {
                        return [];
                    }
                },
                optionTemplate: "partner_autocomplete.DropdownOption",
                placeholder: _t('Searching Autocomplete...'),
            },
        ];
    }

    async onSelect(option) {
        let data = await this.partnerAutocomplete.getCreateData(Object.getPrototypeOf(option));
        if (!data?.company) {
            return;
        }

        if (data.logo) {
            const logoField = this.props.record.resModel === 'res.partner' ? 'image_1920' : 'logo';
            data.company[logoField] = data.logo;
        }

        // Format the many2one fields
        const many2oneFields = ['country_id', 'state_id', 'industry_id'];
        many2oneFields.forEach((field) => {
            if (data.company[field]) {
                data.company[field] = [data.company[field].id, data.company[field].display_name];
            }
        });

        // Save UNSPSC codes (tags)
        const unspsc_codes = data.company.unspsc_codes

        // Delete useless fields before updating record
        data.company = this.partnerAutocomplete.removeUselessFields(data.company, Object.keys(this.props.record.fields));

        // Update record with retrieved values
        if (data.company.name) {
            await this.props.record.update({name: data.company.name});  // Needed otherwise name it is not saved
        }
        await this.props.record.update(data.company);

        // Add UNSPSC codes (tags)
        if (this.props.record.resModel === 'res.partner' && unspsc_codes && unspsc_codes.length !== 0) {
            // We must first save the record so that we can then create the tags (many2many)
            const saved = await this.props.record.save();
            if (saved){
                await this.props.record.load();
                await this.orm.call("res.partner", "iap_partner_autocomplete_add_tags", [this.props.record.resId, unspsc_codes]);
                await this.props.record.load();
            }
        }
        if (this.props.setDirty) {
            this.props.setDirty(false);
        }
    }
}

PartnerAutoCompleteCharField.template = "partner_autocomplete.PartnerAutoCompleteCharField";
PartnerAutoCompleteCharField.components = {
    ...CharField.components,
    PartnerAutoComplete,
};

export const partnerAutoCompleteCharField = {
    ...charField,
    component: PartnerAutoCompleteCharField,
};

registry.category("fields").add("field_partner_autocomplete", partnerAutoCompleteCharField);
