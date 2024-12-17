import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { usePartnerAutocomplete } from "./partner_autocomplete_core";

class PartnerAutoCompleteMany2one extends Component {
    static template = "partner_autocomplete.PartnerAutoCompleteMany2one";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    setup() {
        this.m2o = useMany2One(() => this.props);
        this.partnerAutocomplete = usePartnerAutocomplete();
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            otherSources: this.sources,
        };
    }

    get sources() {
        if (!this.props.canCreate) {
            return [];
        }
        return [this.makePartnerSource()];
    }

    makePartnerSource() {
        return {
            options: async (request) => {
                if (!this.validateSearchTerm(request)) {
                    return [];
                }

                const suggestions = await this.partnerAutocomplete.autocomplete(request);
                for (const suggestion of suggestions) {
                    suggestion.classList = "partner_autocomplete_dropdown_many2one";
                    suggestion.action = this.selectPartnerAutocompleteOption.bind(this);
                }
                return suggestions;
            },
            optionTemplate: "partner_autocomplete.Many2oneDropdownOption",
            placeholder: _t("Searching Autocomplete..."),
        };
    }

    async selectPartnerAutocompleteOption(option, _, { openRecord }) {
        const data = await this.partnerAutocomplete.getCreateData(Object.getPrototypeOf(option));
        const context = { default_is_company: true };
        for (const [key, val] of Object.entries(data.company)) {
            context["default_" + key] = val && val.id ? val.id : val;
        }
        if (data.logo) {
            context.default_image_1920 = data.logo;
        }
        return openRecord({ context });
    }

    validateSearchTerm(request) {
        return request && request.length > 2;
    }
}

registry.category("fields").add("res_partner_many2one", {
    ...buildM2OFieldDescription(PartnerAutoCompleteMany2one),
});
