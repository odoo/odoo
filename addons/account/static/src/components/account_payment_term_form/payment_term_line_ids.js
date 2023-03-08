/** @odoo-module **/

import { registry } from "@web/core/registry";

import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class PaymentTermLineIdsRenderer extends ListRenderer {

    /* override */
    onGlobalClick(ev) {
        // Prevent the discard of new records when clicking outside of the sheet.
        // This is needed because the user is not forced to edit something on the newly
        // created record. Therefore, there is no reason to remove this record when he
        // attempt to save the form.
        this.props.list.editedRecord = null;
        super.onGlobalClick(ev);
    }

}

export class PaymentTermLineIdsOne2Many extends X2ManyField {
    static components = {...X2ManyField.components, ListRenderer: PaymentTermLineIdsRenderer}
}

export const PaymentTermLineIds = {
    ...x2ManyField,
    component: PaymentTermLineIdsOne2Many,
}

registry.category("fields").add("payment_term_line_ids", PaymentTermLineIds);
