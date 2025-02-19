import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Component } from "@odoo/owl";

import { usePartnerAutocomplete } from "@partner_autocomplete/js/partner_autocomplete_core"

class PartnerAutoCompleteMany2one extends Component {
    static template = "partner_autocomplete.PartnerAutoCompleteMany2one";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        super.setup();
        this.partner_autocomplete = usePartnerAutocomplete();
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
                options: async (request) => {
                    if (this.validateSearchTerm(request)) {
                        const suggestions = await this.partner_autocomplete.autocomplete(request);
                        suggestions.forEach((suggestion) => {
                            suggestion.classList = "partner_autocomplete_dropdown_many2one";
                            suggestion.action = this.onSelectPartnerAutocompleteOption.bind(this);
                        });
                        return suggestions;
                    }
                    else {
                        return [];
                    }
                },
                optionTemplate: "partner_autocomplete.Many2oneDropdownOption",
                placeholder: _t("Searching Autocomplete..."),
            },
        ];
    }

    async onSelectPartnerAutocompleteOption(option, params, { openRecord }) {
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
        return openRecord({ context });
    }
}

registry.category("fields").add("res_partner_many2one", {
    ...buildM2OFieldDescription(PartnerAutoCompleteMany2one),
});
