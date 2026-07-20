import { models } from "@web/../tests/web_test_helpers";

export class HrLeaveAccrualLevel extends models.ServerModel {
    _name = "hr.leave.accrual.level";

    _records = [
        // Level 1: Immediate start, Hourly accrual, Lost unused days
        {
            id: 1,
            accrual_plan_id: 1,
            milestone_date: "creation",
            frequency: "hourly",
            added_value: 1,
            added_value_type: "hour",
            action_with_unused_accruals: "lost",
        },
        // Level 2: After 6 Months, Weekly accrual, Unlimited carryover
        {
            id: 2,
            accrual_plan_id: 1,
            milestone_date: "after",
            start_count: 6,
            start_type: "month",
            frequency: "weekly",
            week_day: 0,
            added_value: 4,
            added_value_type: "hour",
            action_with_unused_accruals: "all",
            carryover_options: "unlimited",
        },
        // Level 3: After 1 Year, Monthly accrual with limited carryover & balance cap
        {
            id: 3,
            accrual_plan_id: 1,
            milestone_date: "after",
            start_count: 1,
            start_type: "year",
            frequency: "monthly",
            first_day: 1,
            added_value: 2,
            added_value_type: "day",
            action_with_unused_accruals: "all",
            carryover_options: "limited",
            postpone_max_days: 10,
            maximum_leave: 25,
        },
        // Level 4: After 5 Years, Yearly accrual with yearly cap & balance cap
        {
            id: 4,
            accrual_plan_id: 1,
            milestone_date: "after",
            start_count: 5,
            start_type: "year",
            frequency: "yearly",
            yearly_day: 1,
            yearly_month: "1",
            added_value: 25,
            added_value_type: "day",
            cap_accrued_time_yearly: true,
            cap_accrued_time: true,
            maximum_leave_yearly: 25,
            maximum_leave: 50,
        },
    ];
}
