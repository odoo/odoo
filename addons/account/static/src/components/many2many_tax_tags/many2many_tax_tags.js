import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsField,
    many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";

import { TaxAutoComplete } from "@account/components/tax_autocomplete/tax_autocomplete";

export class Many2ManyTaxTagsAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
        AutoComplete: TaxAutoComplete,
    };
    get SearchMoreButtonLabel() {
        return _t("Not sure... Help me!");
    }

    search(name) {
        return this.orm
            .call(this.props.resModel, "search_read", [], {
                domain: [...this.props.getDomain(), ["name", "ilike", name]],
                fields: ["id", "name", "tax_scope"],
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

    mapRecordToOption(result) {
        return {
            value: result.id,
            label: result.name ? result.name.split("\n")[0] : _t("Unnamed"),
            displayName: result.name,
            tax_scope: result.tax_scope,
        };
    }
}

export class Many2ManyTaxTagsField extends Many2ManyTagsField {
    static components = {
        ...Many2ManyTagsField.components,
        Many2XAutocomplete: Many2ManyTaxTagsAutocomplete,
    };
}

export const many2ManyTaxTagsField = {
    ...many2ManyTagsField,
    component: Many2ManyTaxTagsField,
    additionalClasses: ['o_field_many2many_tags']
};

registry.category("fields").add("many2many_tax_tags", many2ManyTaxTagsField);
