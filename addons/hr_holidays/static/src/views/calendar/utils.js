/**
 * The last moment a leave covers. Days and halves stop on an exclusive bound, so midnight
 * on D+1 still ends D, where hours and all day records name their last day themselves.
 */
export function getLeaveLastMoment(leave) {
    const namesItsLastDay =
        leave.isAllDay || leave.rawRecord?.work_entry_type_request_unit === "hour";
    return namesItsLastDay ? leave.end : leave.end.minus({ millisecond: 1 });
}
