import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Field } from "@web/views/fields/field";

export class PartnerField extends Component {
    static components = { Field };
    static props = {
        ...standardFieldProps,
    };

    static template = "account.PartnerField";

    get nameToDisplay() {
        // If the user is mass editing the partner_id on a move list, this will trigger the list_confirmation_dialog.js that will use this widget again.
        // record.partner_id is already updated in cache with the new partner while record.invoice_partner_display_name is not yet recomputed. So we
        // need to base the output on the partner_id if it's set, and on the computed field if not
        if (this.props.record.data.partner_id) {
            return this.props.record.data.partner_id.display_name;
        }
        return this.props.record.data.invoice_partner_display_name;
    }

}
registry.category("fields").add("partner_field", {
    component: PartnerField,
});
