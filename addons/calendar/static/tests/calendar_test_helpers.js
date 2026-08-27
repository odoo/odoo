import { CalendarEvent } from "./mock_server/mock_models/calendar_event";
import { CalendarAttendee } from "./mock_server/mock_models/calendar_attendee";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { MailActivity } from "./mock_server/mock_models/mail_activity";
import { CalendarFilters } from "./mock_server/mock_models/calendar_filters";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

import { advanceTime, animationFrame } from "@odoo/hoot";
import { click, fill } from "@odoo/hoot-dom";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { findFilterPanelSection } from "@web/../tests/views/calendar/calendar_test_helpers";

export const calendarModels = {
    CalendarAttendee,
    CalendarEvent,
    CalendarFilters,
    ResUsers,
    MailActivity,
};

export function defineCalendarModels() {
    return defineModels({ ...mailModels, ...calendarModels });
}

/**
 * @param {HTMLElement} element
 */
function instantScrollTo(element) {
    element.scrollIntoView({ behavior: "instant", block: "center" });
}

/**
 * @param {string} sectionName
 * @param {string} filterValue
 * @returns {Promise<void>}
 */
export async function togglePartnerFilter(sectionName, filterValue) {
    const root = findFilterPanelSection(sectionName);
    const filter = root.querySelector(`.o_calendar_filter_item_${filterValue}`);
    const input = root.querySelector("input");

    instantScrollTo(input);

    if (filter) {
        await click(filter.querySelector("a.o_delete"));
        await animationFrame();
    } else {
        await click(input);
        await animationFrame();
        await fill(filterValue);
        await animationFrame();
        await click(`a:contains(${filterValue})`);
        await animationFrame();
    }
    await advanceTime(CalendarModel.DEBOUNCED_LOAD_DELAY);
    await animationFrame();
}
