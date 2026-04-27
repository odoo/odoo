import {
    conflictingSlotIdsField,
    ConflictingSlotIdsField,
} from "@planning/components/conflicting_slot_ids_field/conflicting_slot_ids_field";

import { patch } from "@web/core/utils/patch";

patch(ConflictingSlotIdsField.prototype, {
    getConflictSlotMessage(slot) {
        const message = super.getConflictSlotMessage(slot);
        if (!slot.data.sale_line_id) {
            return message;
        } else if (message.length && slot.data.sale_line_id) {
            return `${message} - ${slot.data.sale_line_id}`;
        }
        return slot.data.sale_line_id;
    },
});

const relatedFields = conflictingSlotIdsField.relatedFields;
Object.assign(conflictingSlotIdsField, {
    relatedFields: (fieldInfo) => {
        const fields = relatedFields(fieldInfo);
        fields.push({ name: "sale_line_id", type: "many2one", relation: "sale.order.line" });
        return fields;
    },
});
