/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

export class JournalDashboardActivity extends Component {
    static props = { ...standardFieldProps };

    setup() {
        this.action = useService("action");
        this.MAX_ACTIVITY_DISPLAY = 5;
        this.formatData(this.props);
    }

    formatData(props) {
        this.info = JSON.parse(this.props.record.data[this.props.name]);
        this.info.more_activities = false;
        if (this.info.activities.length > this.MAX_ACTIVITY_DISPLAY) {
            this.info.more_activities = true;
            this.info.activities = this.info.activities.slice(0, this.MAX_ACTIVITY_DISPLAY);
        }
    }

    async openActivity(activity) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Journal Entry'),
            target: 'current',
            res_id: activity.res_id,
            res_model: 'account.move',
            views: [[false, 'form']],
        });
    }

    openAllActivities(e) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: _t('Journal Entries'),
            res_model: 'account.move',
            views: [[false, 'kanban'], [false, 'form']],
            search_view_id: [false],
            domain: [['journal_id', '=', this.props.record.resId], ['activity_ids', '!=', false]],
        });
    }
}
JournalDashboardActivity.template = "account.JournalDashboardActivity";

export const journalDashboardActivity = {
    component: JournalDashboardActivity,
};

registry.category("fields").add("kanban_vat_activity", journalDashboardActivity);
