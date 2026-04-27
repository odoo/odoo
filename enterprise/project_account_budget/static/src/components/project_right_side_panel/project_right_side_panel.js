/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { ProjectRightSidePanel } from '@project/components/project_right_side_panel/project_right_side_panel';

patch(ProjectRightSidePanel.prototype, {
    async loadBudgets() {
        const budgets = await this.orm.call(
            'project.project',
            'get_budget_items',
            [[this.projectId]],
            { context: this.context },
        );
        this.state.data.budget_items = budgets;
        return budgets;
    },

    addBudget() {
        const context = {
            ...this.context,
            project_update: true,
            default_project_id: this.projectId,
            default_company_id:this.state.data.budget_items.company_id,
        };
        this.openFormViewDialog({
            context,
            title: _t('New Budget'),
            resModel: 'budget.analytic',
            onRecordSaved: async () => {
                await this.loadBudgets();
            },
            viewId: this.state.data.budget_items.form_view_id,
        });
    },

    get panelVisible() {
        return super.panelVisible || this.state.data.show_budget_items;
    },
});
