import { models } from "@web/../tests/web_test_helpers";

export class HrVersion extends models.Model {
    _name = "hr.version";

    _records = [
        {
            employee_id: 1,
            contract_date_start: "2025-10-06", // triggers 'new' badge
            contract_date_end: false,
            departure_date: false,
        },
        {
            employee_id: 2,
            contract_date_start: "2025-09-07",
            contract_date_end: "2025-11-07",
            departure_date: "2025-11-07", // triggers 'last' badge
        },
        {
            employee_id: 3,
            contract_date_start: "2025-10-02", // shouldn't trigger 'new' badge
            contract_date_end: false,
            departure_date: false,
        },
    ];
}
