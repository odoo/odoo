import { registry } from "@web/core/registry";
import { Many2One } from "@web/views/fields/many2one/many2one";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class StockLocationAutoComplete extends AutoComplete {
    static template = "stock.StockEmptyLocation";
}

export class StockLocationMany2XAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
        AutoComplete: StockLocationAutoComplete,
    };

    mapRecordToOption(record) {
        const option = super.mapRecordToOption(record);
        option.isEmpty = record.is_empty;
        return option;
    }
}

export class StockLocationMany2One extends Many2One {
    static components = {
        ...Many2One.components,
        Many2XAutocomplete: StockLocationMany2XAutocomplete,
    };

    get many2XAutocompleteProps() {
        const props = super.many2XAutocompleteProps;
        props.specification = {
            ...props.specification,
            is_empty: {},
        };
        return props;
    }
}

export class StockLocationMany2OneField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2One: StockLocationMany2One,
    };
}

registry.category("fields").add("many2one_empty_location", {
    ...buildM2OFieldDescription(StockLocationMany2OneField),
});
