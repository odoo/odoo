import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

// The end resize handle only shows on CSS :hover, which synthetic pointer events
// don't trigger, so give it a grabbable box of its own.
function revealResizeHandle() {
    const resizer = this.anchor.querySelector(".o_calendar_resizer_end");
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
    const startCell = this.anchor.closest(".o_calendar_day[data-date]");
    const nextDate = luxon.DateTime.fromISO(startCell.dataset.date)
        .plus({ days: 1 })
        .toFormat("yyyy-MM-dd");
    const targetCell = `.o_calendar_day[data-date='${nextDate}']`;
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
        const event = document.querySelector(".o_calendar_row_event");
        const cell = document.querySelector(".o_calendar_day[data-date]");
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
            trigger: ".o_calendar_fc_view_dayGridMonth",
        },
        {
            content: "The full-day leave is a resizable all-day event",
            trigger: ".o_calendar_row_event:has(.o_calendar_resizer_end)",
            run: revealResizeHandle,
        },
        {
            content: "Drag its end border onto the next day",
            trigger: ".o_calendar_row_event .o_calendar_resizer_end",
            run: dragHandleToNextDay,
        },
        {
            content: "The leave now spans two days",
            trigger: ".o_calendar_fc_view_dayGridMonth",
            run: waitForExtendedLeave,
        },
    ],
});
