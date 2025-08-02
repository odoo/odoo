import { models } from "@web/../tests/web_test_helpers";

export class ResourceCalendar extends models.ServerModel {
    _name = "resource.calendar";

    _records = [
        {
            id: 1,
            name: "Takeaway",
            attendance_ids: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        },
    ];
}
