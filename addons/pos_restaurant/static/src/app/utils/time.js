const { DateTime, Interval } = luxon;

export function formatDuration(start, end = DateTime.now()) {
    const duration = Interval.fromDateTimes(start, end).toDuration(["hours", "minutes"]);
    if (!duration.isValid || duration.as("minutes") < 1) {
        return false;
    }
    return duration.hours ? duration.toFormat("h'h'm''") : duration.toFormat("m''");
}
