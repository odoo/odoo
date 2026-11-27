import { onMounted, onWillUnmount, proxy } from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
const { DateTime } = luxon;

export function useTime() {
    const state = proxy({ time: "", timeWithoutSeconds: "", day: "", date: "" });
    const timeFormat = localization.timeFormat;
    const dateFormat = localization.dateFormat
        .replace(/MM/g, "LLLL")
        .replace(/\/yy$/, "/yyyy")
        .replace(/[^a-zA-Z]+/g, ", ");
    function setTime() {
        const dateNow = DateTime.now();
        state.time = dateNow.toFormat(timeFormat);
        state.timeWithoutSeconds = dateNow.toFormat(timeFormat.replace(/:ss/, ""));
        state.day = dateNow.toFormat("cccc");
        state.date = dateNow.toFormat(dateFormat);
    }
    let interval;
    onMounted(() => {
        interval = setInterval(() => setTime(), 500);
    });
    onWillUnmount(() => {
        clearInterval(interval);
    });
    setTime();
    return state;
}
