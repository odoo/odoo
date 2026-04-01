import { models } from "@web/../tests/web_test_helpers";

export class ResourceCalendarAttendance extends models.ServerModel {
    _name = "resource.calendar.attendance";

    _load_pos_data_fields() {
        return ["id", "hour_from", "hour_to", "dayofweek", "day_period"];
    }

    _records = [
        {
            id: 1,
            hour_from: 12,
            hour_to: 15,
            dayofweek: "1",
            day_period: "lunch",
        },
        {
            id: 2,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "1",
            day_period: "evening",
        },
        {
            id: 3,
            hour_from: 12,
            hour_to: 15,
            dayofweek: "2",
            day_period: "lunch",
        },
        {
            id: 4,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "2",
            day_period: "evening",
        },
        {
            id: 5,
            hour_from: 12,
            hour_to: 15,
            dayofweek: "3",
            day_period: "lunch",
        },
        {
            id: 6,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "3",
            day_period: "evening",
        },
        {
            id: 7,
            hour_from: 12,
            hour_to: 15,
            dayofweek: "4",
            day_period: "lunch",
        },
        {
            id: 8,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "4",
            day_period: "evening",
        },
        {
            id: 9,
            hour_from: 12,
            hour_to: 15,
            dayofweek: "5",
            day_period: "lunch",
        },
        {
            id: 10,
            hour_from: 18,
            hour_to: 22,
            dayofweek: "5",
            day_period: "evening",
        },
    ];
}
