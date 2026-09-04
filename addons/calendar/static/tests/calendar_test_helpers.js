import { CalendarEvent } from "./mock_server/mock_models/calendar_event";
import { CalendarAttendee } from "./mock_server/mock_models/calendar_attendee";
import { DiscussChannel } from "./mock_server/mock_models/discuss_channel";
import { ResUsers } from "./mock_server/mock_models/res_users";
import { MailActivity } from "./mock_server/mock_models/mail_activity";
import { CalendarFilters } from "./mock_server/mock_models/calendar_filters";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { findFilterPanelSection } from "@web/../tests/views/calendar/calendar_test_helpers";

import { animationFrame } from "@odoo/hoot";
import { click, fill, queryFirst } from "@odoo/hoot-dom";

export const calendarModels = {
    CalendarAttendee,
    CalendarEvent,
    CalendarFilters,
    DiscussChannel,
    ResUsers,
    MailActivity,
};

export function defineCalendarModels() {
    return defineModels({ ...mailModels, ...calendarModels });
}

/**
 * Adds or removes a partner from the "Meet with" attendee filter, rendered as a
 * MultiRecordSelector (tags + a search autocomplete), not a checkbox list.
 *
 * @param {string} sectionName
 * @param {string} partnerName display name of the partner to toggle
 * @returns {Promise<void>}
 */
export async function togglePartnerFilter(sectionName, partnerName) {
    const root = findFilterPanelSection(sectionName);
    const tag = [...root.querySelectorAll(".o_tag")].find((el) =>
        el.textContent.includes(partnerName)
    );

    if (tag) {
        // Remove tag by clicking on the close button.
        tag.scrollIntoView({ behavior: "instant", block: "center" });
        await click(queryFirst("a.o_delete", { root: tag }));
        await animationFrame();
    } else {
        // Add partner by searching for it in the search input autocomplete.
        const input = queryFirst("input", { root });
        input.scrollIntoView({ behavior: "instant", block: "center" });
        await click(input);
        await animationFrame();
        await fill(partnerName);
        await animationFrame();
        await click(`a:contains(${partnerName})`);
        await animationFrame();
    }
    await animationFrame();
}
