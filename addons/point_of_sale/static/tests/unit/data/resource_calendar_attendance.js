import { models } from "@web/../tests/web_test_helpers";

export class ResourceCalendarAttendance extends models.ServerModel {
    _name = "resource.calendar.attendance";

    _load_pos_data_fields() {
        return ["id", "hour_from", "hour_to", "dayofweek", "day_period"];
    }
}
