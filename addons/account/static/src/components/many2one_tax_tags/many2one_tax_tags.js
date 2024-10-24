import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

import { Many2OneField, many2OneField } from "../../../../../web/static/src/views/fields/many2one/many2one_field";

import { TaxAutoComplete } from "@account/components/tax_autocomplete/tax_autocomplete";

export class Many2OneTaxTagsAutocomplete extends Many2XAutocomplete {
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

export class Many2OneTaxTagsField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: Many2OneTaxTagsAutocomplete,
    };
}

export const many2OneTaxTagsField = {
    ...many2OneField,
    component: Many2OneTaxTagsField,
    additionalClasses: ['o_field_many2one']
};

registry.category("fields").add("many2one_tax_tags", many2OneTaxTagsField);
