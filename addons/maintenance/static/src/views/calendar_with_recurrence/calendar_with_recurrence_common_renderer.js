import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";

export class CalendarWithRecurrenceCommonRenderer extends CalendarCommonRenderer {
    onDblClick(info) {
        const record = this.props.model.records[info.event.id];
        this.props.editRecord({ ...record, id: record.rawRecord.id });
    }

    fcEventToRecord() {
        const record = super.fcEventToRecord(...arguments);
        if (record.id) {
            record.id = this.props.model.records[record.id].rawRecord.id;
        }
        return record;
    }

    convertRecordToEvent(record) {
        const event = super.convertRecordToEvent(record);
        // https://fullcalendar.io/docs/editable
        // this is used to disable the 'drag and drop' and 'resizing' for recurring events
        event.editable = !record.isRecurrent;
        return event;
    }
}
