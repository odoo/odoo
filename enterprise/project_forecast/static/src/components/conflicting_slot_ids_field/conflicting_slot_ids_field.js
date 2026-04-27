import {
    conflictingSlotIdsField,
    ConflictingSlotIdsField,
} from "@planning/components/conflicting_slot_ids_field/conflicting_slot_ids_field";

import { patch } from "@web/core/utils/patch";

patch(ConflictingSlotIdsField.prototype, {
    getConflictSlotMessage(slot) {
        const message = super.getConflictSlotMessage(slot);
        if (!slot.data.project_id) {
            return message;
        } else if (message.length && slot.data.project_id) {
            return `${message} - ${slot.data.project_id}`;
        }
        return slot.data.project_id;
    },
});

const relatedFields = conflictingSlotIdsField.relatedFields;
Object.assign(conflictingSlotIdsField, {
    relatedFields: (fieldInfo) => {
        const fields = relatedFields(fieldInfo);
        fields.push({ name: "project_id", type: "many2one", relation: "project.project" });
        return fields;
    },
});
