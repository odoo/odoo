/** @odoo-module **/

import { user } from '@web/core/user';
import { formatFloatTime } from '@web/views/fields/formatters';
import { formatFloat } from "@web/core/utils/numbers";
import { useService } from "@web/core/utils/hooks";
import { HelpdeskTeamTarget } from "../helpdesk_team_target/helpdesk_team_target";
import { Component, useState, onWillStart } from "@odoo/owl";

export class HelpdeskTeamDashboard extends Component {
    static template = "helpdesk.HelpdeskTeamDashboard";
    static components = {
        HelpdeskTeamTarget,
    };
    static props = {};

    setup() {
        this.action = useService('action');
        this.orm = useService('orm');
        this.state = useState({
            dashboardValues: null,
        });

        onWillStart(this.onWillStart);
    }

    get showDemo() {
        return Boolean(this.state.dashboardValues) && this.state.dashboardValues.show_demo;
    }

    get demoClass() {
        return this.showDemo ? 'o_demo o_disabled o_cursor_default' : '';
    }

    async onWillStart() {
        await this._fetchData();
    }

    async updateHelpdeskTarget(targetName, value) {
        await this.orm.write(
            'res.users',
            [user.userId],
            { [targetName]: value },
        );
        this.state.dashboardValues[targetName] = value;
    }

    /**
     * @param {MouseEvent} e
     */
    async onActionClicked(e) {
        if (this.showDemo) {
            return;
        }
        const action = e.currentTarget;
        const actionRef = action.getAttribute('name');
        const title = action.dataset.actionTitle || action.getAttribute('title');
        const searchViewRef = action.getAttribute('search_view_ref');
        const buttonContext = action.getAttribute('context') || '';

        if (action.getAttribute('name').includes('helpdesk.')) {
            return await this.action.doActionButton({
                resModel: 'helpdesk.ticket',
                name: 'create_action',
                args: JSON.stringify([actionRef, title, searchViewRef]),
                context: '',
                buttonContext,
                type: 'object',
            });
        } else {
            if (['action_view_rating_today', 'action_view_rating_7days'].includes(actionRef)) {
                return this.action.doActionButton({
                    resModel: 'helpdesk.team',
                    name: actionRef,
                    context: '',
                    buttonContext,
                    type: 'object',
                });
            }
            return this.action.doAction(actionRef);
        }
    }

    async _fetchData() {
        this.state.dashboardValues = await this.orm.call(
            'helpdesk.team',
            'retrieve_dashboard',
            [],
            { context: user.context },
        );
    }

    formatFloat(value, options = {}) {
        return formatFloat(value, options);
    }

    formatTime(value, options = {}) {
        return formatFloatTime(value, options);
    }

    parseInteger(value) {
        return parseInt(value);
    }
}
