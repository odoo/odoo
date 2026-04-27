import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export function timesheetLeaderboardTimerHook() {
    const orm = useService("orm");
    const companyService = useService("company");

    return {
        getLeaderboardRendering: async () => {
            const read = await orm.read(
                "res.company",
                [companyService.currentCompany.id],
                ["timesheet_show_rates", "timesheet_show_leaderboard"]
            );
            const { timesheet_show_rates, timesheet_show_leaderboard: showLeaderboard } = read[0];
            let showIndicators = timesheet_show_rates;
            if (timesheet_show_rates) {
                const result = await orm.call("hr.employee", "get_billable_time_target", [
                    [user.userId],
                ]);
                const billableTimeTarget = result.length ? result[0].billable_time_target : 0;
                showIndicators = billableTimeTarget > 0;
            }

            return {
                showIndicators: showIndicators,
                showLeaderboard: showLeaderboard,
                showLeaderboardComponent: showIndicators || showLeaderboard,
            };
        },
    };
}
