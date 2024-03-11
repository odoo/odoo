/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import Dialog from 'web.Dialog';

registerModel({
    name: 'DiscussSidebarCategoryItem',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            this.thread.open();
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClickCommandLeave(ev) {
            ev.stopPropagation();
            if (this.channel.channel_type !== 'group' && this.thread.creator === this.messaging.currentUser) {
                await this._askAdminConfirmation();
            }
            if (this.channel.channel_type === 'group') {
                await this._askLeaveGroupConfirmation();
            }
            this.thread.leave();
        },
        /**
         * Redirects to channel form page when `settings` command is clicked.
         *
         * @param {MouseEvent} ev
         */
        onClickCommandSettings(ev) {
            ev.stopPropagation();
            return this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                res_model: this.thread.model,
                res_id: this.thread.id,
                views: [[false, 'form']],
                target: 'current',
            });
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickCommandUnpin(ev) {
            ev.stopPropagation();
            this.thread.unsubscribe();
        },
        /**
         * @private
         * @returns {Promise}
         */
        _askAdminConfirmation() {
            return new Promise(resolve => {
                Dialog.confirm(this,
                    this.env._t("You are the administrator of this channel. Are you sure you want to leave?"),
                    {
                        buttons: [
                            {
                                text: this.env._t("Leave"),
                                classes: 'btn-primary',
                                close: true,
                                click: resolve,
                            },
                            {
                                text: this.env._t("Discard"),
                                close: true,
                            },
                        ],
                    }
                );
            });
        },
        /**
         * @private
         * @returns {Promise}
         */
        _askLeaveGroupConfirmation() {
            return new Promise(resolve => {
                Dialog.confirm(this,
                    this.env._t("You are about to leave this group conversation and will no longer have access to it unless you are invited again. Are you sure you want to continue?"),
                    {
                        buttons: [
                            {
                                text: this.env._t("Leave"),
                                classes: 'btn-primary',
                                close: true,
                                click: resolve
                            },
                            {
                                text: this.env._t("Discard"),
                                close: true
                            }
                        ]
                    }
                );
            });
        },
    },
    fields: {
        /**
         * Image URL for the related channel thread.
         */
        avatarUrl: attr({
            compute() {
                switch (this.channel.channel_type) {
                    case 'channel':
                    case 'group':
                        return `/web/image/mail.channel/${this.channel.id}/avatar_128?unique=${this.channel.avatarCacheKey}`;
                    case 'chat':
                        if (this.channel.correspondent) {
                            return this.channel.correspondent.avatarUrl;
                        }
                }
                return '/mail/static/src/img/smiley/avatar.jpg';
            },
        }),
        /**
         * Determines the discuss sidebar category displaying this item.
         */
        category: one('DiscussSidebarCategory', {
            identifying: true,
            inverse: 'categoryItems',
        }),
        /**
         * Determines the contribution of this discuss sidebar category item to
         * the counter of this category.
         */
        categoryCounterContribution: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                switch (this.channel.channel_type) {
                    case 'channel':
                        return this.thread.message_needaction_counter > 0 ? 1 : 0;
                    case 'chat':
                    case 'group':
                        return this.channel.localMessageUnreadCounter > 0 ? 1 : 0;
                }
            },
        }),
        channel: one('Channel', {
            identifying: true,
            inverse: 'discussSidebarCategoryItem',
        }),
        /**
         * Amount of unread/action-needed messages
         */
        counter: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                switch (this.channel.channel_type) {
                    case 'channel':
                        return this.thread.message_needaction_counter;
                    case 'chat':
                    case 'group':
                        return this.channel.localMessageUnreadCounter;
                }
            },
        }),
        /**
         * Boolean determines whether the item has a "leave" command
         */
        hasLeaveCommand: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                return (
                    ['channel', 'group'].includes(this.channel.channel_type) &&
                    !this.thread.message_needaction_counter &&
                    !this.thread.group_based_subscription
                );
            },
        }),
        /**
         * Boolean determines whether the item has a "settings" command.
         */
        hasSettingsCommand: attr({
            compute() {
                return this.channel.channel_type === 'channel';
            },
        }),
        /**
         * Boolean determines whether ThreadIcon will be displayed in UI.
         */
        hasThreadIcon: attr({
            compute() {
                if (!this.thread) {
                    return clear();
                }
                switch (this.channel.channel_type) {
                    case 'channel':
                        return !Boolean(this.thread.authorizedGroupFullName);
                    case 'chat':
                        return true;
                    case 'group':
                        return false;
                }
            },
        }),
        /**
         * Boolean determines whether the item has a "unpin" command.
         */
        hasUnpinCommand: attr({
            compute() {
                return this.channel.channel_type === 'chat' && !this.channel.localMessageUnreadCounter;
            },
        }),
        /**
         * Boolean determines whether the item is currently active in discuss.
         */
        isActive: attr({
            compute() {
                return this.messaging.discuss && this.thread === this.messaging.discuss.activeThread;
            },
        }),
        /**
         * Boolean determines whether the item has any unread messages.
         */
        isUnread: attr({
            compute() {
                return this.channel.localMessageUnreadCounter > 0;
            },
        }),
        /**
         * The related thread.
         */
        thread: one('Thread', {
            related: 'channel.thread'
        }),
    },
});
