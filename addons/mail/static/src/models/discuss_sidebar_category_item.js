/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import Dialog from 'web.Dialog';

registerModel({
    name: 'DiscussSidebarCategoryItem',
    recordMethods: {
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeAvatarUrl() {
            if (!this.channel) {
                return clear();
            }
            switch (this.channel.channel_type) {
                case 'channel':
                case 'group':
                    return `/web/image/mail.channel/${this.channel.id}/avatar_128?unique=${this.thread.avatarCacheKey}`;
                case 'chat':
                    if (this.thread.correspondent) {
                        return this.thread.correspondent.avatarUrl;
                    }
            }
            return '/mail/static/src/img/smiley/avatar.jpg';
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeCategoryCounterContribution() {
            if (!this.channel) {
                return clear();
            }
            switch (this.channel.channel_type) {
                case 'channel':
                    return this.thread.message_needaction_counter > 0 ? 1 : 0;
                case 'chat':
                case 'group':
                    return this.thread.localMessageUnreadCounter > 0 ? 1 : 0;
            }
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeCounter() {
            if (!this.channel) {
                return clear();
            }
            switch (this.channel.channel_type) {
                case 'channel':
                    return this.thread.message_needaction_counter;
                case 'chat':
                case 'group':
                    return this.thread.localMessageUnreadCounter;
            }
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasLeaveCommand() {
            if (!this.channel) {
                return clear();
            }
            return (
                ['channel', 'group'].includes(this.channel.channel_type) &&
                !this.thread.message_needaction_counter &&
                !this.thread.group_based_subscription
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSettingsCommand() {
            return this.channel.channel_type === 'channel';
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasUnpinCommand() {
            if (!this.channel) {
                return clear();
            }
            return this.channel.channel_type === 'chat' && !this.thread.localMessageUnreadCounter;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsActive() {
            return this.messaging.discuss && this.thread === this.messaging.discuss.thread;
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsUnread() {
            return this.thread.localMessageUnreadCounter > 0;
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeHasThreadIcon() {
            if (!this.channel) {
                return clear();
            }
            switch (this.channel.channel_type) {
                case 'channel':
                    return ['private', 'public'].includes(this.thread.public);
                case 'chat':
                    return true;
                case 'group':
                    return false;
            }
        },
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
            compute: '_computeAvatarUrl',
        }),
        /**
         * Determines the discuss sidebar category displaying this item.
         */
        category: one('DiscussSidebarCategory', {
            identifying: true,
            inverse: 'categoryItems',
            readonly: true,
            required: true,
        }),
        /**
         * Determines the contribution of this discuss sidebar category item to
         * the counter of this category.
         */
        categoryCounterContribution: attr({
            compute: '_computeCategoryCounterContribution',
            readonly: true,
        }),
        channel: one('Channel', {
            readonly: true,
            related: 'thread.channel',
        }),
        /**
         * Amount of unread/action-needed messages
         */
        counter: attr({
            compute: '_computeCounter',
        }),
        /**
         * Boolean determines whether the item has a "leave" command
         */
        hasLeaveCommand: attr({
            compute: '_computeHasLeaveCommand',
        }),
        /**
         * Boolean determines whether the item has a "settings" command.
         */
        hasSettingsCommand: attr({
            compute: '_computeHasSettingsCommand',
        }),
        /**
         * Boolean determines whether ThreadIcon will be displayed in UI.
         */
        hasThreadIcon: attr({
            compute: '_computeHasThreadIcon',
        }),
        /**
         * Boolean determines whether the item has a "unpin" command.
         */
        hasUnpinCommand: attr({
            compute: '_computeHasUnpinCommand',
        }),
        /**
         * Boolean determines whether the item is currently active in discuss.
         */
        isActive: attr({
            compute: '_computeIsActive',
        }),
        /**
         * Boolean determines whether the item has any unread messages.
         */
        isUnread: attr({
            compute: '_computeIsUnread',
        }),
        /**
         * The related thread.
         */
        thread: one('Thread', {
            identifying: true,
            inverse: 'discussSidebarCategoryItem',
            readonly: true,
            required: true,
        }),
    },
});
