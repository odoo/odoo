import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

// The end resize handle only shows on CSS :hover, which synthetic pointer events
// don't trigger, so give it a grabbable box of its own.
function revealResizeHandle() {
    const resizer = this.anchor.querySelector(".fc-event-resizer-end");
    if (!resizer) {
        throw new Error("The leave event has no end resize handle");
    }
    Object.assign(resizer.style, {
        display: "block",
        position: "absolute",
        width: "8px",
        height: "100%",
        right: "0",
        top: "0",
    });
}

async function dragHandleToNextDay(helpers) {
    const startCell = this.anchor.closest(".fc-daygrid-day[data-date]");
    const nextDate = luxon.DateTime.fromISO(startCell.dataset.date)
        .plus({ days: 1 })
        .toFormat("yyyy-MM-dd");
    const targetCell = `.fc-daygrid-day[data-date='${nextDate}']`;
    if (!document.querySelector(targetCell)) {
        throw new Error(`No day cell for ${nextDate} in the current month grid`);
    }
    // Center: the default "top" would drop one pixel above the cell, on the previous week.
    await helpers.drag_and_drop(targetCell, { position: "center" });
}

// The drop writes through the backend and the calendar reloads asynchronously.
async function waitForExtendedLeave() {
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    for (let i = 0; i < 50; i++) {
        await sleep(100);
        const event = document.querySelector(".fc-daygrid-block-event");
        const cell = document.querySelector(".fc-daygrid-day[data-date]");
        if (
            event &&
            cell &&
            event.getBoundingClientRect().width > cell.getBoundingClientRect().width * 1.4
        ) {
            return;
        }
    }
    throw new Error("The leave did not extend after the resize drag");
}

registry.category("web_tour.tours").add("time_off_resize_month_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: '.o_app[data-menu-xmlid="hr_holidays.menu_hr_holidays_root"]',
            run: "click",
        },
        {
            content: "Open the scale selector",
            trigger: ".scale_button_selection",
            run: "click",
        },
        {
            content: "Switch to Month view",
            trigger: ".o_scale_button_month",
            run: "click",
        },
        {
            content: "Month grid is shown",
            trigger: ".fc-dayGridMonth-view",
        },
        {
            content: "The full-day leave is a resizable all-day event",
            trigger: ".fc-daygrid-block-event.fc-event-resizable",
            run: revealResizeHandle,
        },
        {
            content: "Drag its end border onto the next day",
            trigger: ".fc-daygrid-block-event.fc-event-resizable .fc-event-resizer-end",
            run: dragHandleToNextDay,
        },
        {
            content: "The leave now spans two days",
            trigger: ".fc-dayGridMonth-view",
            run: waitForExtendedLeave,
        },
    ],
});
