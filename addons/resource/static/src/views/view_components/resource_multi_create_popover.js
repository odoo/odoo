import { MultiCreatePopover } from "@web/views/view_components/multi_create_popover";
import { AttendanceDurationKeeper } from "@resource/components/resource_calendar_attendance_popover/attendance_duration_keeper";

export class ResourceMultiCreatePopover extends MultiCreatePopover {
    /**
     * @override
     */
    setup() {
        super.setup();
        const durationKeeper = new AttendanceDurationKeeper();
        const { onRootLoaded } = this.multiCreateRecordProps.hooks;
        this.multiCreateRecordProps.hooks = {
            onRootLoaded: (record) => {
                onRootLoaded(record);
                durationKeeper.track(record);
            },
            onRecordChanged: (record) => durationKeeper.onRecordChanged(record),
        };
    }
}
