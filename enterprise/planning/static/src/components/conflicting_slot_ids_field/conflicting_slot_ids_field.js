import { registry } from "@web/core/registry";
import { formatFloatTime } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { getFormattedValue } from "@web/views/utils";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class ConflictingSlotIdsField extends Component {
    static template = "planning.ConflictingSlotIdsField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.actionService = useService("action");
    }

    get conflictingSlots() {
        return this.props.record.data[this.props.name].records.map((r) => ({
            ...r,
            data: Object.fromEntries(
                Object.keys(r.data).map((fieldName) => {
                    let formattedValue = "";
                    if (fieldName === "allocated_hours") {
                        formattedValue = formatFloatTime(r.data.allocated_hours, {
                            noLeadingZeroHour: true,
                        }).replace(/(:00|:)/g, "h");
                    } else {
                        formattedValue = getFormattedValue(r, fieldName);
                    }
                    if (fieldName === "allocated_percentage") {
                        formattedValue += "%";
                    }
                    return [fieldName, formattedValue];
                })
            ),
        }));
    }

    getConflictSlotMessage(slot) {
        return slot.data.role_id;
    }

    async showConflictedSlots() {
        if (this.props.record.isNew) {
            await this.props.record.save({ noReload: true });
        }
        this.actionService.doActionButton({
            type: "object",
            resId: this.props.record.resId,
            name: "action_see_overlaping_slots",
            resModel: "planning.slot",
        });
    }
}

export const conflictingSlotIdsField = {
    component: ConflictingSlotIdsField,
    supportedTypes: ["many2many"],
    relatedFields: () => {
        return [
            { name: "start_datetime", type: "datetime" },
            { name: "end_datetime", type: "datetime" },
            { name: "allocated_hours", type: "float_time" },
            { name: "allocated_percentage", type: "float" },
            { name: "role_id", type: "many2one", relation: "planning.role" },
        ];
    },
};

registry.category("fields").add("conflicting_slot_ids", conflictingSlotIdsField);
