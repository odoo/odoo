/** The last moment a leave covers: days and halves stop on an exclusive bound. */
export function getLeaveLastMoment(leave) {
    const namesItsLastDay =
        leave.isAllDay || leave.rawRecord?.time_type_request_unit === "hour";
    return namesItsLastDay ? leave.end : leave.end.minus({ millisecond: 1 });
}
