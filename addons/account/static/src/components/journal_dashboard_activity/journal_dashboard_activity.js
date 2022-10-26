/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

export class JournalDashboardActivity extends Component {
    setup() {
        this.action = useService("action");
        this.MAX_ACTIVITY_DISPLAY = 5;
        this.formatData(this.props);
    }

    formatData(props) {
        this.info = JSON.parse(this.props.value);
        this.info.more_activities = false;
        if (this.info.activities.length > this.MAX_ACTIVITY_DISPLAY) {
            this.info.more_activities = true;
            this.info.activities = this.info.activities.slice(0, this.MAX_ACTIVITY_DISPLAY);
        }
    }

    async openActivity(activity) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: this.env._t('Journal Entry'),
            target: 'current',
            res_id: activity.res_id,
            res_model: 'account.move',
            views: [[false, 'form']],
        });
    }

    openAllActivities(e) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: this.env._t('Journal Entries'),
            res_model: 'account.move',
            views: [[false, 'kanban'], [false, 'form']],
            search_view_id: [false],
            domain: [['journal_id', '=', this.props.record.resId], ['activity_ids', '!=', false]],
        });
    }
}
JournalDashboardActivity.template = "account.JournalDashboardActivity";

registry.category("fields").add("kanban_vat_activity", JournalDashboardActivity);
