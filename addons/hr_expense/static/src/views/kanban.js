import { registry } from '@web/core/registry';

import { ExpenseDashboard } from "@hr_expense/components/expense_dashboard";
import { useUploadOnHelperClick } from "@hr_expense/views/upload_helper_hook";

import { kanbanView } from '@web/views/kanban/kanban_view';
import { KanbanController } from '@web/views/kanban/kanban_controller';
import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { user } from "@web/core/user";
import { rpc } from "@web/core/network/rpc";
import { onWillStart } from "@odoo/owl";

export class ExpenseKanbanController extends KanbanController {
    setup() {
        super.setup();
        onWillStart(async () => {
            [this.userIsExpenseTeamApprover, this.userHasEmployee] = await Promise.all([
                user.hasGroup("hr_expense.group_hr_expense_team_approver"),
                rpc(
                    "/web/dataset/call_kw/res.users/read",
                    {
                        model: "res.users",
                        method: "read",
                        args: [[user.userId], ["employee_id"]],
                        kwargs: { context: user.context },
                    },
                    { cache: { type: "disk" } }
                ).then((r) => !!r?.[0]?.employee_id),
            ]);
        });
    }

    get canCreate() {
        if (!this.userHasEmployee && !this.userIsExpenseTeamApprover) {
            return false;
        }
        return super.canCreate;
    }
}

export class ExpenseKanbanRenderer extends KanbanRenderer {
    static template = "hr_expense.KanbanRenderer";

    setup() {
        super.setup();
        useUploadOnHelperClick(this.rootRef);
    }
}

export class ExpenseDashboardKanbanRenderer extends ExpenseKanbanRenderer {
    static components = { ...ExpenseDashboardKanbanRenderer.components, ExpenseDashboard };
    static template = "hr_expense.DashboardKanbanRenderer";
}

registry.category('views').add('hr_expense_kanban', {
    ...kanbanView,
    Controller: ExpenseKanbanController,
    Renderer: ExpenseKanbanRenderer,
});

registry.category('views').add('hr_expense_dashboard_kanban', {
    ...kanbanView,
    Controller: ExpenseKanbanController,
    Renderer: ExpenseDashboardKanbanRenderer,
});
