import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { TaxAutoComplete } from "@account/components/tax_autocomplete/tax_autocomplete";

export class Many2XTaxTagsAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
        AutoComplete: TaxAutoComplete,
    };

    async loadOptionsSource(request) {
        // Always include Search More
        let options = await super.loadOptionsSource(...arguments);
        if (!options?.slice(-1)[0].classList?.includes("o_m2o_dropdown_option_search_more")) {
            options.push({
                label: this.SearchMoreButtonLabel,
                action: this.onSearchMore.bind(this, request),
                classList: "o_m2o_dropdown_option o_m2o_dropdown_option_search_more",
            });
        }
        return options;
    }

    search(name) {
        return this.orm
            .call(this.props.resModel, "search_read", [], {
                domain: [...this.props.getDomain(), ["name", "ilike", name]],
                fields: ["id", "display_name", "tax_scope"],
                context: this.props.context,
            })
            .then((records) => {
                return this.orm
                    .call("account.tax", "fields_get", [], { attributes: ["selection"] })
                    .then((fields) => {
                        const selectionOptions = fields.tax_scope.selection;

                        const recordsWithLabels = records.map((record) => {
                            const selectedOption = selectionOptions.find(
                                (option) => option[0] === record.tax_scope
                            );
                            const label = selectedOption ? selectedOption[1] : undefined;
                            return { ...record, tax_scope: label };
                        });

                        return recordsWithLabels;
                    });
            });
    }

    async onSearchMore(request) {
        const { resModel, getDomain, context, fieldString } = this.props;

        const domain = getDomain();
        let dynamicFilters = [];
        if (request.length) {
            const nameGets = await this.orm.call(resModel, "name_search", [], {
                name: request,
                domain: domain,
                operator: "ilike",
                limit: this.props.searchMoreLimit,
                context,
            });

            dynamicFilters = [
                {
                    description: _t("Quick search: %s", request),
                    domain: [["id", "in", nameGets.map((nameGet) => nameGet[0])]],
                },
            ];
        }

        const filterFP = context.dynamic_fiscal_position_id;
        if (filterFP) {
            dynamicFilters.push({
                description: _t("Document Fiscal Position"),
                domain: [["fiscal_position_ids", "in", [parseInt(filterFP)]]]
            })
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
