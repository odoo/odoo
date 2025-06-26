import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

export class Many2XTaxTagsAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
    };

    async loadOptionsSource(request) {
        // Always include Search More
        let options = await super.loadOptionsSource(...arguments);
        if (!options.slice(-1)[0]?.cssClass?.includes("o_m2o_dropdown_option_search_more")) {
            options.push({
                label: this.SearchMoreButtonLabel,
                onSelect: this.onSearchMore.bind(this, request),
                cssClass: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            });
        }
        return options;
    }

    async onSearchMore(request) {
        const { getDomain, context, fieldString } = this.props;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            dynamicFilters = [
                {
                    description: _t("Quick search: %s", request),
                    domain: [["name", "ilike", request]],
                },
            ];
        }

        const title = _t("Search: %s", fieldString);
        this.selectCreate({
            domain,
            context,
            filters: dynamicFilters,
            title,
        });
    }

}

export class Many2ManyTaxTagsField extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        Many2XAutocomplete: Many2XTaxTagsAutocomplete,
    };
}

export const many2ManyTaxTagsField = {
    ...many2ManyTagsField,
    component: Many2ManyTaxTagsField,
    additionalClasses: ['o_field_many2many_tags']
};

registry.category("fields").add("many2many_tax_tags", many2ManyTaxTagsField);
