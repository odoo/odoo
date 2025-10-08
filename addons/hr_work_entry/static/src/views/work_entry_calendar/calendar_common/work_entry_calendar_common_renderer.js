import { convertRecordToEvent } from "@web/views/calendar/utils";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { WorkEntryPopover } from "@hr_work_entry/components/work_entry_popover/work_entry_popover";
import { useService } from "@web/core/utils/hooks";
import { formatFloatTime } from "@web/views/fields/formatters";

export class WorkEntryCalendarCommonRenderer extends CalendarCommonRenderer {
    static eventTemplate = "hr_work_entry.WorkEntryCalendarCommonRenderer.event";
    static components = {
        ...CalendarCommonRenderer,
        Popover: WorkEntryPopover,
    };

    setup() {
        super.setup();
        this.workEntryPopoverModel = useService("workEntryPopoverService");
        this.workEntryPopoverModel.setup(this.props.model.meta, this.additionalFieldsToFetch);
    }

    get additionalFieldsToFetch() {
        return [
            { name: "employee_id", type: "many2one", readonly: false },
            { name: "version_id", type: "many2one", readonly: false },
            { name: "date", type: "date", readonly: false },
            { name: "is_manual", type: "boolean", readonly: false },
        ];
    }

    /**
     * @override
     */
    convertRecordToEvent(record) {
        const event = convertRecordToEvent(record);
        const editable = record.rawRecord.state !== "validated" && (event.editable ?? null);
        return {
            ...event,
            ...(editable ? { editable: editable } : {}),
        };
    }

    /**
     * @override
     */
    getPopoverProps(record) {
        record = record.rawRecord;
        return {
            readonly: !this.props.editRecord || record.state === "validated",
            onReload: async () => await this.props.model.load(),
            originalRecord: record,
            editArchInfo: this.editArchInfo,
            getDurationStr: (duration) =>
                formatFloatTime(duration, {
                    noLeadingZeroHour: true,
                }).replace(/(:00|:)/g, "h"),
            recordProps: this.workEntryPopoverModel.recordProps,
            archInfo: this.workEntryPopoverModel.archInfo,
            getSource: this.workEntryPopoverModel.getSource,
        };
    }
}
