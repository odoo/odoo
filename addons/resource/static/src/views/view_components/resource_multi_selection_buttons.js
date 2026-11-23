import { usePlugin } from "@odoo/owl";
import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";
import { ResourceMultiCreatePopover } from "@resource/views/view_components/resource_multi_create_popover";

export class ResourceMultiSelectionButtons extends MultiSelectionButtons {
    static components = {
        ...MultiSelectionButtons.components,
        Popover: ResourceMultiCreatePopover,
    };

    /**
     * @override
     */
    setup() {
        super.setup();
        this.resourceCalendarPlugin = usePlugin(ResourceCalendarPlugin);
    }

    /**
     * @override
     */
    getMultiCreatePopoverProps() {
        const props = super.getMultiCreatePopoverProps();
        const hoursPerDay = this.resourceCalendarPlugin.record?.data.hours_per_day;
        if (!hoursPerDay) {
            return props;
        }
        const recordProps = props.multiCreateRecordProps;
        const values = recordProps.values;
        if (!values) {
            recordProps.context = { ...recordProps.context, default_duration_hours: hoursPerDay };
        } else if (!values.duration_hours || values.duration_hours === this.defaultDuration) {
            recordProps.values = { ...values, ...this.getHoursForDuration(values, hoursPerDay) };
        }
        this.defaultDuration = hoursPerDay;
        return props;
    }

    getHoursForDuration({ hour_from, hour_to }, duration) {
        if (!hour_from && !hour_to) {
            return { duration_hours: duration };
        }
        if (hour_from + duration > 24) {
            return { duration_hours: duration, hour_from: 24 - duration, hour_to: 24 };
        }
        return { duration_hours: duration, hour_to: hour_from + duration };
    }

    /**
     * @override
     */
    computeValues(record) {
        const values = super.computeValues(...arguments);
        if (values.recurrency_end_type !== "date") {
            delete values.recurrency_until;
        }
        return values;
    }
}
