import { models } from "@web/../tests/web_test_helpers";

export class ResourceCalendarAttendance extends models.ServerModel {
    _name = "resource.calendar.attendance";

    _load_pos_data_fields() {
        return ["id", "hour_from", "hour_to", "dayofweek"];
    }

    _records = [
        {
            id: 1,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "1",
        },
        {
            id: 2,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "2",
        },
        {
            id: 3,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "3",
        },
        {
            id: 4,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "4",
        },
        {
            id: 5,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "5",
        },
    ];
}
