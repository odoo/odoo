import { models } from "@web/../tests/web_test_helpers";

export class HrWorkEntryType extends models.ServerModel {
    _name = "hr.work.entry.type";

    _records = [
        {
            id: 1,
            name: "Test Work Entry Type",
            color: 1,
            display_code: "WT1",
        },
        {
            id: 2,
            name: "WET no color",
            color: false,
            display_code: "WT2",
        },
        {
            id: 3,
            name: "WET no display code",
            color: 1,
            display_code: false,
        },
    ];
}
