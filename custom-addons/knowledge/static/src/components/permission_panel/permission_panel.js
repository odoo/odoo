/** @odoo-module **/

import { session } from "@web/session";
import { ConfirmationDialog, AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from '@web/core/utils/hooks';
import { Component, onWillStart, useEffect, useState} from "@odoo/owl";

const permissionLevel = {'none': 0, 'read': 1, 'write': 2}
const restrictMessage = _t("Are you sure you want to restrict access to this article? "
+ "This means it will no longer inherit access rights from its parents.");
const loseWriteMessage = _t('Are you sure you want to remove your own "Write" access?');

export class PermissionPanel extends Component {
    /**
     * @override
     */
    setup () {
        this.actionService = useService('action');
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.rpc = useService('rpc');
        /** @type {import("@mail/core/common/thread_service").ThreadService} */
        this.threadService = useService("mail.thread");
        this.userService = useService('user');

        this.state = useState({
            loading: true,
            partner_id: session.partner_id
        });
        onWillStart(async () => {
            this.isInternalUser = await this.userService.hasGroup('base.group_user');
        });
        useEffect(() => {
            this.loadPanel();
        }, () => [this.props.record.resId]);
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
        return this.rpc("/knowledge/get_article_permission_panel_data",
            {
                article_id: this.props.record.resId
            }
        );
    }

    /**
     * @returns {Array[Array]}
     */
    getInternalPermissionOptions () {
        return this.state.internal_permission_options;
    }

    /**
     * @param {Proxy} member
     * @returns {Boolean}
     */
    isLoggedUser (member) {
        return member.partner_id === session.partner_id;
    }

    _onInviteMembersClick () {
        this.env._saveIfDirty();
        this.actionService.doAction('knowledge.knowledge_invite_action_from_article', {
            additionalContext: {active_id: this.props.record.resId},
            onClose: async () => {
                // Update panel content
                await this.loadPanel();
                // Reload record
                this.env.model.root.load();

            }
        });
    }

    /**
     * Callback function called when the internal permission of the article changes.
     * @param {Event} event
     */
    _onChangeInternalPermission (event) {
        const $select = $(event.target);
        const index = this.state.members.findIndex(current => {
            return current.partner_id === session.partner_id;
        });
        const newPermission = $select.val();
        const oldPermission = this.state.internal_permission;
        const willRestrict = this.state.based_on && permissionLevel[newPermission] < permissionLevel[oldPermission]
                                && permissionLevel[newPermission] < permissionLevel[this.state.parent_permission];
        const willLoseAccess = $select.val() === 'none' && (index >= 0 && this.state.members[index].permission === 'none');
        const confirm = async () => {
            const res = await this.rpc('/knowledge/article/set_internal_permission',
                {
                    article_id: this.props.record.resId,
                    permission: newPermission,
                }
            );
            if (this._onChangedPermission(res, willLoseAccess)) {
                this.loadPanel();
            }
        };

        if (!willLoseAccess && !willRestrict) {
            confirm();
            return;
        }

        const discard = () => {
            $select.val(oldPermission);
            this.loadPanel();
        };
        const loseAccessMessage = _t('Are you sure you want to set the internal permission to "none"? If you do, you will no longer have access to the article.');
        const confirmLabel = willLoseAccess ? _t('Lose Access') : _t('Restrict Access');
        const confirmTitle = willLoseAccess ? false : _t('Restrict Access');
        this._showConfirmDialog(willLoseAccess ? loseAccessMessage : restrictMessage, confirmTitle, { confirmLabel, confirm, cancel: discard });
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
        const willLoseAccess = this.isLoggedUser(member) && newPermission === 'none';
        const willRestrict = this.state.based_on && permissionLevel[newPermission] < permissionLevel[oldPermission];
        const willLoseWrite = this.isLoggedUser(member) && newPermission !== 'write' && oldPermission === 'write';
        const willGainWrite = this.isLoggedUser(member) && newPermission === 'write' && oldPermission !== 'write';
        const confirm = async () => {
            const res = await this.rpc('/knowledge/article/set_member_permission',
                {
                    article_id: this.props.record.resId,
                    permission: newPermission,
                    member_id: member.based_on ? false : member.id,
                    inherited_member_id: member.based_on ? member.id: false,
                }
            );
            const reloadArticleId = willLoseWrite && !willLoseAccess ? this.props.record.resId : false;
            if (this._onChangedPermission(res, willLoseAccess || willLoseWrite, reloadArticleId)) {
                this.loadPanel();
            }
        };

        if (!willLoseAccess && !willRestrict && !willLoseWrite) {
            await confirm();
            if (willGainWrite) {
                // Reload article when admin gives himself write access
                this.env.model.root.load();
            }
            return;
        }

        const discard = () => {
            $select.val(this.state.members[index].permission);
            this.loadPanel();
        };
        const loseAccessMessage = _t('Are you sure you want to set your permission to "none"? If you do, you will no longer have access to the article.');
        const message = willLoseAccess ? loseAccessMessage : willLoseWrite ? loseWriteMessage : restrictMessage ;
        const title = willLoseAccess ? _t('Leave Article') : _t('Change Permission');
        const confirmLabel = willLoseAccess ? _t('Lose Access') : this.isLoggedUser(member) ? _t('Restrict own access') : _t('Restrict Access');
        this._showConfirmDialog(message, title, { confirmLabel, confirm, cancel: discard } );
    }

    /**
     * Callback function called when a member is removed.
     * @param {Event} event
     * @param {Proxy} member
     */
    _onRemoveMember (event, member) {
        if (!this.state.members.includes(member)) {
            return;
        }

        const willRestrict = member.based_on ? true : false;
        const willLoseAccess = this.isLoggedUser(member) && member.permission !== "none";
        const confirm = async () => {
            const res = await this.rpc('/knowledge/article/remove_member',
                {
                    article_id: this.props.record.resId,
                    member_id: member.based_on ? false : member.id,
                    inherited_member_id: member.based_on ? member.id: false,
                }
            );
            if (this._onChangedPermission(res, willLoseAccess)) {
                this.loadPanel();
            }
        };

        if (!willLoseAccess && !willRestrict) {
            confirm();
            return;
        }

        const discard = () => {
            this.loadPanel();
        };

        let message = restrictMessage;
        let title = _t('Restrict Access');
        let confirmLabel = title;
        if (this.isLoggedUser(member) && this.state.category === 'private') {
            message = _t('Are you sure you want to leave your private Article? As you are its last member, it will be moved to the Trash.');
            title = _t('Leave Private Article');
            confirmLabel = _t('Move to Trash');
        } else if (willLoseAccess) {
            message = _t('Are you sure you want to remove your member? By leaving an article, you may lose access to it.');
            title = _t('Leave Article');
            confirmLabel = _t('Leave');
        }

        this._showConfirmDialog(message, title, { confirmLabel, confirm, cancel: discard });
    }

    /**
     * Callback function called when user clicks on 'Restore' button.
     * @param {Event} event
     */
    _onRestore (event) {
        const articleId = this.props.record.resId;
        const confirm = async () => {
            const res = await this.orm.call(
                'knowledge.article',
                'restore_article_access',
                [[articleId]],
            );
            if (res) {
                if (this._onChangedPermission({success: res})) {
                    this.loadPanel();
                }
            }
        };

        const message = _t('Are you sure you want to restore access? This means this article will now inherit any access set on its parent articles.');
        const title = _t('Restore Access');
        const confirmLabel = _t('Restore Access');
        this._showConfirmDialog(message, title, { confirmLabel, confirm });
    }

    /**
     * @param {Event} event
     * @param {Proxy} member
     */
    async _onMemberAvatarClick (event, member) {
        if (!member.partner_share) {
            const partnerRead = await this.orm.read(
                'res.partner',
                [member.partner_id],
                ['user_ids'],
            );
            const userIds = partnerRead && partnerRead.length === 1 ? partnerRead[0]['user_ids'] : false;
            const userId = userIds && userIds.length === 1 ? userIds[0] : false;

            if (userId) {
                this.threadService.openChat({ userId });
            }
        }
    }

  /**
    * This method is called before each permission change rpc when the user needs to confirm the change as them
    * would lose them access to the article if them do confirm.
    * @param {str} message
    * @param {function} confirm
    * @param {function} discard
    * @param {str} confirmLabel
    */
    _showConfirmDialog (message, title, options) {
        options = options || {};
        if (!options.cancel) {
            options.cancel = this.loadPanel.bind(this);
        }
        this.dialog.add(ConfirmationDialog, {
            title: title || _t("Confirmation"),
            body: message,
            ...options
        });
    }

  /**
    * This method is called after each permission change rpc.
    * It will check if a reloading of the article tree or a complete reload is needed in function
    * of the new article state (if change of category or if user lost their own access to the current article).
    * return True if the caller should continue after executing this method, and False, if caller should stop.
    * @param {Dict} result
    * @param {Boolean} lostAccess
    */
    async _onChangedPermission (result, reloadAll, reloadArticleId) {
        if (result.error) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: result.error,
            });
        } else if (reloadAll && reloadArticleId) {  // Lose write access
            if (await this.props.record.isDirty()) {
                await this.props.record.save({ reload: false });
            }
            await this.env.model.root.load();
            return false;
        } else if (reloadAll) {  // Lose access -> Hard Reload
            window.location.replace('/knowledge/home');
        } else if (result.new_category) {
            if (await this.props.record.isDirty()) {
                await this.props.record.save();
            }
            await this.env.model.root.load();
        }
        return true;
    }

    async _onChangeVisibility (event) {
        const $input = $(event.target);
        const articleId = this.props.record.resId;
        await this.orm.call(
            'knowledge.article',
            'set_is_article_visible_by_everyone',
            [articleId, $input.val() === 'everyone']
        );
        if (await this.props.record.isDirty()) {
            await this.props.record.save();
        }
        await this.props.record.load();
    }
}

PermissionPanel.template = 'knowledge.PermissionPanel';
PermissionPanel.props = {
    record: Object,
};

export default PermissionPanel;
