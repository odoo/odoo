/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export class BankRecMany2OneMultiID extends Many2OneField {

    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        if (this.props.record.selected && this.props.record.model.multiEdit) {
            props.context.active_ids = this.env.model.root.selection.map((r) => r.resId);
        }
        return props;
    }
}

export const bankRecMany2OneMultiID = {
    ...many2OneField,
    component: BankRecMany2OneMultiID,
};

registry.category("fields").add("bank_rec_list_many2one_multi_id", bankRecMany2OneMultiID);
