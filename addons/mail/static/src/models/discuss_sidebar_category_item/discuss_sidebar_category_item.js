/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { clear, link } from '@mail/model/model_field_command';
import { isEventHandled } from '@mail/utils/utils';

import Dialog from 'web.Dialog';

function factory(dependencies) {
    class DiscussSidebarCategoryItem extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            this.onClick = this.onClick.bind(this);
            this.onClickCommandLeave = this.onClickCommandLeave.bind(this);
            this.onClickCommandSettings = this.onClickCommandSettings.bind(this);
            this.onClickCommandUnpin = this.onClickCommandUnpin.bind(this);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            switch (this.channelType) {
                case 'channel':
                case 'group':
                    return `/web/image/mail.channel/${this.channel.id}/avatar_128?unique=${this.channel.avatarCacheKey}`;
                case 'chat':
                    if (this.channel.correspondent) {
                        return this.channel.correspondent.avatarUrl;
                    }
            }
            return '/mail/static/src/img/smiley/avatar.jpg';
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeCategoryCounterContribution() {
            switch (this.channel.channel_type) {
                case 'channel':
                    return this.channel.message_needaction_counter > 0 ? 1 : 0;
                case 'chat':
                case 'group':
                    return this.channel.localMessageUnreadCounter > 0 ? 1 : 0;
            }
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeCounter() {
            switch (this.channelType) {
                case 'channel':
                    return this.channel.message_needaction_counter;
                case 'chat':
                case 'group':
                    return this.channel.localMessageUnreadCounter;
            }
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasLeaveCommand() {
            return (
                ['channel', 'group'].includes(this.channelType) &&
                !this.channel.message_needaction_counter &&
                !this.channel.group_based_subscription
            );
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasSettingsCommand() {
            return this.channelType === 'channel';
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasUnpinCommand() {
            return this.channelType === 'chat' && !this.channel.localMessageUnreadCounter;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsActive() {
            return this.messaging.discuss && this.channel === this.messaging.discuss.thread;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsUnread() {
            if (!this.channel) {
                return clear();
            }
            return this.channel.localMessageUnreadCounter > 0;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasThreadIcon() {
            switch (this.channelType) {
                case 'channel':
                    return ['private', 'public'].includes(this.channel.public);
                case 'chat':
                    return true;
                case 'group':
                    return false;
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @param {MouseEvent} ev
         */
        onClick(ev) {
            if (isEventHandled(ev, 'EditableText.click')) {
                return;
            }
            this.channel.open();
        }

        /**
         * @param {MouseEvent} ev
         */
        async onClickCommandLeave(ev) {
            ev.stopPropagation();
            if (this.channel.channel_type !== 'group' && this.channel.creator === this.messaging.currentUser) {
                await this._askAdminConfirmation();
            }
            if (this.channel.channel_type === 'group') {
                await this._askLeaveGroupConfirmation();
            }
            this.channel.leave();
        }

        /**
         * Redirects to channel form page when `settings` command is clicked.
         *
         * @param {MouseEvent} ev
         */
        onClickCommandSettings(ev) {
            ev.stopPropagation();
            return this.env.bus.trigger('do-action', {
                action: {
                    type: 'ir.actions.act_window',
                    res_model: this.channel.model,
                    res_id: this.channel.id,
                    views: [[false, 'form']],
                    target: 'current',
                },
            });
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickCommandUnpin(ev) {
            ev.stopPropagation();
            this.channel.unsubscribe();
        }

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
        }

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
        }

    }

    DiscussSidebarCategoryItem.fields = {
        /**
         * Image URL for the related channel thread.
         */
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        /**
         * Determines the discuss sidebar category displaying this item.
         */
        category: many2one('mail.discuss_sidebar_category', {
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
         * The related channel thread.
         */
        channel: one2one('mail.thread', {
            inverse: 'discussSidebarCategoryItem',
            readonly: true,
            required: true,
        }),
        /**
         * Type of the related channel thread.
         */
        channelType: attr({
            related: 'channel.channel_type',
        }),

    };
    DiscussSidebarCategoryItem.identifyingFields = ['category', 'channel'];
    DiscussSidebarCategoryItem.modelName = 'mail.discuss_sidebar_category_item';

    return DiscussSidebarCategoryItem;
}

registerNewModel('mail.discuss_sidebar_category_item', factory);
