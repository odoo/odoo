import { providePlugins, useScope, usePlugin } from "@odoo/owl";
import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";
import { ResourceCalendarPlugin } from "@resource/plugins/resource_calendar_plugin";

export class ResourceMultiSelectionButtons extends MultiSelectionButtons {
    /**
     * @override
     */
    setup() {
        super.setup();
        if (!useScope().pluginManager.getPluginById(ResourceCalendarPlugin.id)) {
            providePlugins([ResourceCalendarPlugin]);
        }
        this.resourceCalendarPlugin = usePlugin(ResourceCalendarPlugin);
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

    /**
     * @override
     */
    getMultiCreatePopoverProps() {
        const props = super.getMultiCreatePopoverProps();
        const hoursPerDay = this.resourceCalendarPlugin.record?.data.hours_per_day || 1;
        const { values } = props.multiCreateRecordProps;
        props.multiCreateRecordProps = {
            ...props.multiCreateRecordProps,
            // first Add, set default duration
            context: {
                ...props.multiCreateRecordProps.context,
                default_duration_hours: hoursPerDay,
            },
            // On later Adds, duration must be refreshed
            values: values && { ...values, duration_hours: hoursPerDay },
        };
        return props;
    }
}
