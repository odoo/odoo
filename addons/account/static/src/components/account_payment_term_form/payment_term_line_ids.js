/** @odoo-module **/

import { registry } from "@web/core/registry";

import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

export class PaymentTermLineIdsOne2Many extends X2ManyField {
    /**
     * Override to mark all new records as 'dirty' by calling update with an empty object.
     * This prevents the records from being abandoned if the user clicks globally or on an existing
     * record.
     */
    async addInlineRecord() {
        const newRecord = await super.addInlineRecord(...arguments);
        newRecord.update({});
    }
}

export const PaymentTermLineIds = {
    ...x2ManyField,
    component: PaymentTermLineIdsOne2Many,
}

registry.category("fields").add("payment_term_line_ids", PaymentTermLineIds);
