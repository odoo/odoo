import { expect, test } from "@odoo/hoot";
import { defineModels, mountView } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { HrLeaveAccrualPlan } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave_accrual_plan";
import { HrLeaveAccrualLevel } from "@hr_holidays/../tests/mock_server/mock_models/hr_leave_accrual_level";

defineModels([HrLeaveAccrualPlan, HrLeaveAccrualLevel]);
defineMailModels();

test("accrual levels widget rendering with diverse level configurations", async () => {
    await mountView({
        type: "form",
        resModel: "hr.leave.accrual.plan",
        arch: `
            <form>
                <field name="carryover_date" invisible="1"/>
                <field name="carryover_day" invisible="1"/>
                <field name="carryover_month" invisible="1"/>
                <field name="level_ids" widget="accrual_levels"/>
            </form>
        `,
        resId: 1,
    });

    // 1 Header + 4 Levels + 1 Add button = 6 total timeline rows
    expect(".o_accrual_level").toHaveCount(6);

    // Verify Level 1 (Immediately)
    const level1 = ".o_accrual_level:nth-child(2)";
    expect(`${level1} .time`).toHaveText("Immediately");
    expect(`${level1} .content`).toHaveText(
        "Accrual frequency : 1 hour\(s\) every hour\.\n\nUnused days will be reset\."
    );

    // Verify Level 2 (After 6 Months)
    const level2 = ".o_accrual_level:nth-child(3)";
    expect(`${level2} .time`).toHaveText("After 6 month\(s\)");
    expect(`${level2} .content`).toHaveText(
        "Accrual frequency : 4 hour\(s\) every week on Monday\.\n\nUnused days will be transferred totally on each start of the year\."
    );

    // Verify Level 3 (After 1 Year with Limited Carryover & Balance Cap)
    const level3 = ".o_accrual_level:nth-child(4)";
    expect(`${level3} .time`).toHaveText("After 1 year\(s\)");
    expect(`${level3} .content`).toHaveText(
        "Accrual frequency : 2 day\(s\) every month on the 1 of the month\.\n\nUnused days will be transferred with a max of 10 day\(s\) on each start of the year.\nA balance cap is set to 25 day\(s\)\."
    );

    // Verify Level 4 (After 5 Years with Yearly Cap + Balance Cap)
    const level4 = ".o_accrual_level:nth-child(5)";
    expect(`${level4} .time`).toHaveText("After 5 year(s)");
    expect(`${level4} .content`).toHaveText(
        "Accrual frequency : 25 day(s) every year on the 1 of January.\n\nUnused days will be transferred with a max of 0 day\(s\) on each start of the year.\nA yearly cap is set to 25 day(s) and a balance cap is set to 50 day(s).");
});
