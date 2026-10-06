import { getLocalYearAndWeek } from "@web/core/l10n/dates";

export function makeWeekColumn({ el, weekText }) {
    for (const headerCell of el.querySelectorAll(".o_calendar_header_cell:first-child")) {
        const weekHeader = document.createElement("div");
        weekHeader.classList.add("o_calendar_week_header");
        weekHeader.innerText = weekText;
        headerCell.before(weekHeader);
    }
    for (const row of el.querySelectorAll(".o_calendar_day_row")) {
        const { date } = row.querySelector(".o_calendar_day[data-date]").dataset;
        const week = document.createElement("div");
        week.classList.add("o_calendar_week");
        const number = document.createElement("span");
        number.classList.add("px-1");
        number.innerText = getLocalYearAndWeek(luxon.DateTime.fromISO(date)).week;
        week.append(number);
        row.prepend(week);
    }
}
