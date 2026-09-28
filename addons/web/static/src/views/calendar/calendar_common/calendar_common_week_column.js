import { getLocalYearAndWeek } from "@web/core/l10n/dates";

export function makeWeekColumn({ el, weekText }) {
    for (const headerCell of el.querySelectorAll(".fc-col-header-cell:first-child")) {
        const weekHeader = document.createElement("div");
        weekHeader.classList.add("o-fc-week-header");
        weekHeader.innerText = weekText;
        headerCell.before(weekHeader);
    }
    for (const row of el.querySelectorAll(".fc-daygrid-row")) {
        const { date } = row.querySelector(".fc-daygrid-day[data-date]").dataset;
        const week = document.createElement("div");
        week.classList.add("o-fc-week");
        week.innerText = getLocalYearAndWeek(luxon.DateTime.fromISO(date)).week;
        row.prepend(week);
    }
}
