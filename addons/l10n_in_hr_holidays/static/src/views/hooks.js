export function useExceptionalDays(props) {
    return (info) => {
        const date = luxon.DateTime.fromJSDate(info.date).toISODate();
        const exceptionalDays = props.model.exceptionalDays[date];
        if (exceptionalDays) {
            return [`hr_exceptional_day hr_mandatory_day hr_mandatory_day_${exceptionalDays}`];
        }
        return [];
    };
}
