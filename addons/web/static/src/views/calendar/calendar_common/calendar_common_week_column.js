// @ts-check

/** @module @web/views/calendar/calendar_common/calendar_common_week_column - Inserts week-number columns into FullCalendar grid headers and body rows */

/**
 * Insert a dedicated week-number column into a FullCalendar grid.
 *
 * Prepends header and body cells with week numbers before the first column
 * of each row in the calendar element.
 *
 * @param {Object} params
 * @param {HTMLElement} params.el - FullCalendar root element
 * @param {boolean} params.showWeek - whether week numbers are enabled
 * @param {boolean} params.weekColumn - whether to render as a separate column
 * @param {string} params.weekText - header label for the week column
 */
export function makeWeekColumn({ el, showWeek, weekColumn, weekText }) {
    const firstRows = el.querySelectorAll(
        ".fc-col-header-cell:nth-child(1), .fc-day:nth-child(1)",
    );
    for (const element of firstRows) {
        const newElement = document.createElement("th");
        if (element.classList.contains("fc-col-header-cell")) {
            newElement.classList.add("o-fc-week-header");
            newElement.innerText = weekText;
        } else {
            newElement.classList.add("o-fc-week");
            const weekElement = element.querySelector(".fc-daygrid-week-number");
            weekElement.classList.remove("fc-daygrid-week-number");
            newElement.append(weekElement);
        }
        element.parentElement.insertBefore(newElement, element);
    }
}
