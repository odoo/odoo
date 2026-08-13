export function makeWeekColumn({ el, showWeek, weekColumn, weekText }) {
    const firstRows = el.querySelectorAll(".fc-col-header-cell:nth-child(1), .fc-day:nth-child(1)");
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
