/** @odoo-module **/
/* Copyright 2023 Tecnativa - Stefan Ungureanu
 * License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl). */

import {CalendarCommonRenderer} from "@web/views/calendar/calendar_common/calendar_common_renderer";
import {patch} from "@web/core/utils/patch";

patch(
    CalendarCommonRenderer.prototype,
    "WebCalendarSlotDurationCalendarCommonRenderer",
    {
        get options() {
            const options = this._super(...arguments);
            if (this.env.searchModel.context.calendar_slot_duration) {
                options.slotDuration =
                    this.env.searchModel.context.calendar_slot_duration;
            }
            return options;
        },
    }
);
