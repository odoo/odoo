import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { Component, onMounted } from "@odoo/owl";


class SlotPickerField extends Component {
    static template = "event.SlotPickerField";
    static props = {
        ...standardFieldProps,
        endDatetimeField: { type: String },
        readonly: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.actionService = useService("action");

        onMounted(() => {
            this.env.bus.addEventListener("slot_selected", res => this.updateField(res.detail));
        });
    }

    get startDatetimeField() {
        return this.props.name;
    }

    get endDatetimeField() {
        return this.props.endDatetimeField;
    }

    clearSlot() {
        this.updateField([false, false]);
    }

    getFormattedValue() {
        if (!this.props.record.data[this.startDatetimeField] || !this.props.record.data[this.endDatetimeField]) {
            return "";
        }
        const date = formatDate(this.props.record.data[this.startDatetimeField]);
        const start = formatDateTime(this.props.record.data[this.startDatetimeField], { 'showSeconds': false }).split(" ")[1];
        const end = formatDateTime(this.props.record.data[this.endDatetimeField], { 'showSeconds': false }).split(" ")[1];
        return `${date}, ${start} - ${end}`;
    }

    openSlotPicker() {
        this.actionService.doAction("event.action_open_event_slot_calendar", {
            additionalContext: {
                slots_selectable: true,
                event_id: this.props.record.data.event_id[0],
            },
        });
    }

    updateField(value) {
        if (!value) {
            return;
        }
        this.props.record.update({
            [this.startDatetimeField]: value[0],
            [this.endDatetimeField]: value[1],
        });
    }
}

const slotPickerField = {
    component: SlotPickerField,
    displayName: _t("Slot picker"),
    extractProps: ({ attrs, options }, dynamicInfo) => ({
        endDatetimeField: options['end_datetime_field'],
        readonly: Boolean(attrs.readonly),
    }),
};

registry.category("fields").add("slot_picker", slotPickerField);
