import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import {
    Many2ManyTagsFieldColorEditable,
    many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import {
    Many2OneField,
    many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { UomAutoComplete } from "@uom/components/uom_autocomplete/uom_autocomplete";

export class Many2XUomTagsAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
        AutoComplete: UomAutoComplete,
    };

    async search(name) {
        const records = await this.orm.searchRead(
            this.props.resModel,
            [...this.props.getDomain(), ["name", "ilike", name]], 
            ["id", "name", "relative_factor", "relative_uom_id"],
        );
        return records.map((record) => {
            return {
                ...record,
                relative_info: record.relative_uom_id ? `${record.relative_factor} ${record.relative_uom_id[1]}` : undefined,
            };
        });
    }

    mapRecordToOption(result) {
        return {
            value: result.id,
            label: result.name ? result.name.split("\n")[0] : _t("Unnamed"),
            displayName: result.name,
            relative_info: result.relative_info,
        };
    }
}

export class Many2ManyUomTagsField extends Many2ManyTagsFieldColorEditable {
    static components = {
        ...Many2ManyTagsFieldColorEditable.components,
        Many2XAutocomplete: Many2XUomTagsAutocomplete,
    };
}

export class Many2OneUomField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: Many2XUomTagsAutocomplete,
    };
}   

export const many2ManyUomTagsField = {
    ...many2ManyTagsFieldColorEditable,
    component: Many2ManyUomTagsField,
    additionalClasses: ['o_field_many2many_tags'],
};

export const many2OneUomField = {
    ...many2OneField,
    component: Many2OneUomField,
    additionalClasses: ['o_field_many2one'],
};

registry.category("fields").add("many2many_uom_tags", many2ManyUomTagsField);
registry.category("fields").add("many2one_uom", many2OneUomField);
