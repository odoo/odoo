import { useState, useEffect } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
const { DateTime } = luxon;

export function useTime() {
    const state = useState({ hours: "", day: "", date: "" });
    const timeFormat = localization.timeFormat;
    const dateFormat = localization.dateFormat
        .replace(/MM/g, "LLLL")
        .replace(/\/yy$/, "/yyyy")
        .replace(/[^a-zA-Z]+/g, ", ");
    function setTime() {
        const dateNow = DateTime.now();
        state.hours = dateNow.toFormat(timeFormat);
        state.day = dateNow.toFormat("cccc");
        state.date = dateNow.toFormat(dateFormat);
    }
    useEffect(
        () => {
            const interval = setInterval(() => setTime(), 500);

            return () => {
                clearInterval(interval);
            };
        },
        () => []
    );
    setTime();
    return state;
}
