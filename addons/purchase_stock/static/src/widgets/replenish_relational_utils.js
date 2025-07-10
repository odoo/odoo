import { registry } from "@web/core/registry";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

class ReplenishAutoComplete extends AutoComplete {
    // static template = "purchase_stock.ReplenishAutoComplete";
    onOptionClick(option) {
        super.onOptionClick(option);
    }
}

class ReplenishMany2XAutoComplete extends Many2XAutocomplete {
    static template = "purchase_stock.ReplenishMany2XAutocomplete";
    static components = { ReplenishAutoComplete };

    setup() {
        super.setup();
    }

    mapRecordToOption(result) {
        const res = super.mapRecordToOption(result);
        if (!result[2].is_vendor) {
            res.classList += ' o_replenish_autocomplete_partner_link';
            res.openEditForm = true;
            res.partner_id = result[2].partner_id;
        } else {
            res.openEditForm = false;
        }
        return res;
    }

    onSelect(option, params = {}) {
        if (option.openEditForm == false) {
            return super.onSelect(option, params);
        }

        const record = {
            id: option.value,
            // bit hacky: passing partner_id for name_create
            display_name: option.partner_id,
        };
        this.props.update([record], params);
        option.action(params);
    }

    async loadOptionsSource(request) {
        const res = await super.loadOptionsSource(request);
        const options = res.map(r => {
            if (r.openEditForm) {
                r.action = () => this.openMany2X({
                    context: this.getCreationContext(request),
                    nextRecordsContext: this.props.context,
                })
            }

            return r;
        })
        return options;
    }
}

class ReplenishMany2OneField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: ReplenishMany2XAutoComplete,
    };
}

registry.category("fields").add("replenish_many2one", {
    ...many2OneField,
    component: ReplenishMany2OneField,
});
