/** @odoo-module **/

import { user } from "@web/core/user";
import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart, useState } from "@odoo/owl";

export class PermissionPanel extends Component {
    static template = "project.PermissionPanel";
    static props = {
        record: Object,
    };

    /**
     * @override
     */
    setup () {
        this.actionService = useService('action');
        this.orm = useService('orm');

        this.state = useState({
            loading: true,
            partner_id: user.partnerId
        });
        onWillStart(async () => {
            this.loadPanel();
            this.isInternalUser = await user.hasGroup('base.group_user');
        });
    }

    async loadPanel () {
        Object.assign(this.state, {
            ...await this.loadData(),
            loading: false
        });
    }

    /**
     * @returns {Object}
     */
    loadData () {
        return this.orm.call('project.project', 'get_project_permission_panel_data', [this.props.record.resId]);
    }

    /**
     * @param {Proxy} member
     * @returns {Boolean}
     */
    isLoggedUser (member) {
        return member.partner_id === user.partnerId;
    }

    async _onInviteMembersClick() {
        if (await this.props.record.isDirty()) {
            await this.props.record.save();
        }
        await this.actionService.doAction('project.project_share_wizard_action', {
            additionalContext: {active_id: this.props.record.resId, res_model: this.props.record.resId},
            res_id: this.props.record.resId,
            onClose: async () => {
                // Update panel content
                await this.loadPanel();
                // Reload record
                this.env.model.root.load();
            }
        });
    }

    /**
     * Callback function called when the permission of a user changes.
     * @param {Event} event
     * @param {Proxy} member
     */
    async _onChangeMemberPermission (event, member) {
        const index = this.state.members.indexOf(member);
        if (index < 0) {
            return;
        }
        const $select = $(event.target);
        const newPermission = $select.val();
        const oldPermission = member.permission;
        if (newPermission != oldPermission){
            await this.orm.call('project.project', 'set_portal_permission', [this.props.record.resId, newPermission, member.id,]);
            // Update panel content
            this.loadPanel();
            // Reload record
            await this.env.model.root.load();
        }
    }

    /**
     * Callback function called when a member is removed.
     * @param {Event} event
     * @param {Proxy} member
     */
    async _onRemoveMember (event, member) {
        if (!this.state.members.includes(member)) {
            return;
        }
        await this.orm.call('project.project', 'remove_collaborator_follower', [this.props.record.resId, member.id]);
        // Update panel content
        await this.loadPanel();
        // Reload record
        this.env.model.root.load();
    }
}

export default PermissionPanel;
