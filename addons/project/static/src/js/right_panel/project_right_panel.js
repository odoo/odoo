/** @odoo-module **/

import { AddMilestone, OpenMilestone } from '@project/js/right_panel/project_utils';
import { formatFloat } from "@web/fields/formatters";
const { useState } = owl.hooks;

export default class ProjectRightPanel extends owl.Component {
    constructor() {
        super(...arguments);
        this.context = this.props.action.context;
        this.domain = this.props.action.domain;
        this.project_id = this.context.active_id;
        this.state = useState({
            data: {
                milestones: {
                    data: []
                },
                user: {},
            }
        });
    }

    formatFloat(value) {
        return formatFloat(value, { digits: [false, 1] });
    }

    async willStart() {
        await super.willStart(...arguments);
        await this._loadQwebContext();
    }

    async willUpdateProps() {
        await super.willUpdateProps(...arguments);
        await this._loadQwebContext();
    }

    async _loadQwebContext() {
        if (!this.project_id){ // If this is called from notif, multiples updates but no specific project
            return {};
        }
        const data = await this.rpc({
            model: 'project.project',
            method: 'get_panel_data',
            args: [this.project_id],
            kwargs: {
                context: this.context
            }
        });
        this.state.data = data;
        return data;
    }

    async onProjectActionClick(event) {
        event.stopPropagation();
        let action = event.currentTarget.dataset.action;
        const additionalContext = JSON.parse(event.currentTarget.dataset.additional_context || "{}");
        if (event.currentTarget.dataset.type === "object") {
            action = await this.rpc({
                // Use the call_button method in order to have an action
                // with the correct view naming, i.e. list view is named
                // 'list' rather than 'tree'.
                route: '/web/dataset/call_button',
                params: {
                    model: 'project.project',
                    method: event.currentTarget.dataset.action,
                    args: [this.project_id],
                    kwargs: {
                        context: this.context
                    }
                }
            });
        }
        this._doAction(action, {
            additional_context: additionalContext
        });
    }

    _doAction(action, options) {
        this.trigger('do-action', {
            action,
            options
        });
    }
}

ProjectRightPanel.template = "project.ProjectRightPanel";
ProjectRightPanel.components = {AddMilestone, OpenMilestone};
