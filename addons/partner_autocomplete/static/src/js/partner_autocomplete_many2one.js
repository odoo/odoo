import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Component } from "@odoo/owl";
import { Many2XAutocomplete, useOpenMany2XRecord } from "@web/views/fields/relational_utils";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core";
import { PartnerAutoComplete } from "@partner_autocomplete/js/partner_autocomplete_component";

export class PartnerMany2XAutocomplete extends Many2XAutocomplete {
    static components = {
        ...super.components,
        AutoComplete: PartnerAutoComplete,
    };
}
export class PartnerMany2One extends Many2One {
    static components = {
        ...super.components,
        Many2XAutocomplete: PartnerMany2XAutocomplete,
    };
}

export class PartnerAutoCompleteMany2one extends Component {
    static template = "partner_autocomplete.PartnerAutoCompleteMany2one";
    static components = { Many2One: PartnerMany2One };
    static props = { ...Many2OneField.props };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.partnerAutocomplete = usePartnerAutocomplete();
        this.openRecord = useOpenMany2XRecord({
            resModel: this.props.record.fields[this.props.name].relation,
            activeActions: {
                create: this.props.canCreate,
                createEdit: this.props.canCreateEdit,
                write: this.props.canWrite,
            },
            isToMany: false,
            onRecordSaved: (record) => this.props.record.update({
                [this.props.name]: {
                    id: record.resId,
                    display_name: record.data.display_name || record.data.name,
                },
            }),
            onRecordDiscarded: () => this.props.record.update(false),
            fieldString: this.props.string || this.props.record.fields[this.props.name].string,
        });
    }

    validateSearchTerm(request) {
        return request && request.length > 2;
    }

    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            otherSources: this.sources,
        };
    }

    get sources() {
        if (!this.props.canCreate) {
            return [];
        }
        return [
            {
                options: async (request, shouldSearchWorldWide) => {
                    if (this.validateSearchTerm(request)) {
                        let queryCountryId = false;
                    	if (shouldSearchWorldWide){
							queryCountryId = 0;
						}
                        const suggestions = await this.partnerAutocomplete.autocomplete(request, queryCountryId);
                        return suggestions.map((suggestion) => ({
                            cssClass: "partner_autocomplete_dropdown_many2one",
                            data: suggestion,
                            label: suggestion.name,
                            onSelect: () => this.onSelectPartnerAutocompleteOption(suggestion),
                        }));
                    }
                    else {
                        return [];
                    }
                },
                optionSlot: "partnerOption",
                placeholder: _t("Searching Autocomplete..."),
            },
        ];
    }

    async onSelectPartnerAutocompleteOption(option) {
        const data = await this.partnerAutocomplete.getCreateData(option);
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

        const unspsc_codes = data.company.unspsc_codes;
        if(unspsc_codes){
            context.default_category_id = await this.orm.call("res.partner", "iap_partner_autocomplete_get_tag_ids", [[], unspsc_codes]);
        }

        return this.openRecord({ context });
    }
}

export const PartnerAutoCompleteMany2oneField = {
    ...buildM2OFieldDescription(PartnerAutoCompleteMany2one),
};

registry.category("fields").add("res_partner_many2one", PartnerAutoCompleteMany2oneField);
