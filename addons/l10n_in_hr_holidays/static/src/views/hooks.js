import { serializeDate } from "@web/core/l10n/dates";

export function useOptionalHolidays(props) {
    return (info) => {
        const date = serializeDate(luxon.DateTime.fromJSDate(info.date))
        const optional = props.model.optionalDays.includes(date) || false;
        return optional ? ["o_optional_holidays"] : [];
    };
}
