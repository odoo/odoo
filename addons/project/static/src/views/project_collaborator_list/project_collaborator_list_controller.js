/** @odoo-module */

import { ListController } from '@web/views/list/list_controller';

export class ProjectCollaboratorsListController extends ListController {

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onClickInviteCollaborators(ev) {
        ev.preventDefault();
        this.actionService.doAction('project.project_share_wizard_action', {
            additionalContext: {
                'default_access_mode': 'edit',
                'active_model': 'project.project',
                'active_id': this.props.context.active_id,
            },
            onClose: async () => {
                await this.model.load();
                this.model.notify();
            },
        });
    }
}
