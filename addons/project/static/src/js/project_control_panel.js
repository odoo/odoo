/** @odoo-module **/

import ControlPanel from 'web.ControlPanel';
import session from 'web.session';

const { onWillStart, onWillUpdateProps } = owl;

export class ProjectControlPanel extends ControlPanel {

    setup() {
        super.setup();
        this.show_project_update = this.props.view.type === "form" || this.props.action.context.show_project_update;
        this.project_id = this.show_project_update ? this.props.action.context.active_id : false;

        onWillStart(() => this._loadWidgetData());
        onWillUpdateProps(() => this._loadWidgetData());
    }

    async _loadWidgetData() {
        if (this.show_project_update) {
            this.data = await this.rpc({
                model: 'project.project',
                method: 'get_last_update_or_default',
                args: [this.project_id],
            });
            this.is_project_user = await session.user_has_group('project.group_project_user');
        }
    }

    async onStatusClick(ev) {
        ev.preventDefault();
        await this.trigger('do-action', {
            action: "project.project_update_all_action",
            options: {
                additional_context: {
                    default_project_id: this.project_id,
                    active_id: this.project_id
                }
            }
        });
    }
}
