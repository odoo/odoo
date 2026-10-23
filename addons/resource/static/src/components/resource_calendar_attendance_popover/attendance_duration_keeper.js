export class AttendanceDurationKeeper {
    track(record) {
        const { hour_from, hour_to, duration_hours } = record.data;
        this.lastHours = { hour_from, hour_to, duration_hours };
    }

    onRecordChanged(record) {
        const previous = this.lastHours;
        this.track(record);
        const { hour_from, hour_to } = record.data;
        if (!previous || hour_from === previous.hour_from) {
            return;
        }
        const isEndTimeUnchanged =
            hour_to === previous.hour_to || (!previous.hour_to && hour_to === hour_from);
        if (!isEndTimeUnchanged) {
            return;
        }
        const newHourTo = Math.min(hour_from + previous.duration_hours, 24);
        if (newHourTo !== hour_to) {
            record.update({ hour_to: newHourTo });
        }
    }
}
