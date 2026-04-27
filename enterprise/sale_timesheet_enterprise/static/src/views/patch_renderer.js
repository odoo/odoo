import { onWillStart } from "@odoo/owl";
import { TimesheetLeaderboard } from "@sale_timesheet_enterprise/components/timesheet_leaderboard/timesheet_leaderboard";
import { timesheetLeaderboardTimerHook } from "@sale_timesheet_enterprise/hooks/timesheet_leaderboard_timer_hook";
import { patch } from "@web/core/utils/patch";

export function patchRenderer(Renderer) {
    patch(Renderer.components, { TimesheetLeaderboard });
    patch(Renderer.prototype, {
        setup() {
            super.setup();
            const { getLeaderboardRendering } = timesheetLeaderboardTimerHook();
            onWillStart(async () => {
                const { showIndicators, showLeaderboard, showLeaderboardComponent } = await getLeaderboardRendering();
                this.showIndicators = showIndicators;
                this.showLeaderboard = showLeaderboard;
                this.showLeaderboardComponent = showLeaderboardComponent;
            });
        },
    });
}
