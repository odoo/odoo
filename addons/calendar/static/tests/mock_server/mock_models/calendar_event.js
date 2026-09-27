import { serializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";

import { models, fields, serverState } from "@web/../tests/web_test_helpers";

const { DateTime } = luxon;

export function todayMeetingDomain() {
    const today = DateTime.now();
    return [
        ["start", "<=", serializeDateTime(today.endOf("day"))],
        ["stop", ">=", serializeDateTime(today.startOf("day"))],
    ];
}

export class CalendarEvent extends models.ServerModel {
    _name = "calendar.event";

    start = fields.Datetime();
    stop = fields.Datetime();
    user_id = fields.Generic({ default: serverState.userId });
    partner_id = fields.Generic({ default: serverState.partnerId });
    partner_ids = fields.Generic({ default: [[6, 0, [serverState.partnerId]]] });

    has_access() {
        return true;
    }

    get_default_duration() {
        return 3.25;
    }

    get_discuss_videocall_location() {
        return `${getOrigin()}/calendar/join_videocall/testtoken`;
    }

    _store_calendar_event_fields(res) {
        res.extend(["name", "start", "stop", "location"]);
        res.many("partner_ids", ["name"]);
    }
}
