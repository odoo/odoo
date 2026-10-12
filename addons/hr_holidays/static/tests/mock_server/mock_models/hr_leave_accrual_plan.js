import { models } from "@web/../tests/web_test_helpers";

export class HrLeaveAccrualPlan extends models.ServerModel {
    _name = "hr.leave.accrual.plan";

    _records = [
        {
            id: 1,
            can_be_carryover: true,
            carryover_date: "year_start",
            carryover_day: "1",
            carryover_month: "1",
            level_ids: [1, 2, 3, 4],
        },
    ];
}
