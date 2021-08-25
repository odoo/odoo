/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear, link } from '@mail/model/model_field_command';
import { isEventHandled } from '@mail/utils/utils';

import Dialog from 'web.Dialog';

function factory(dependencies) {
    class DiscussSidebarCategoryItem extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            this.onCancelRenaming = this.onCancelRenaming.bind(this);
            this.onClick = this.onClick.bind(this);
            this.onClickCommandLeave = this.onClickCommandLeave.bind(this);
            this.onClickCommandRename = this.onClickCommandRename.bind(this);
            this.onClickCommandSettings = this.onClickCommandSettings.bind(this);
            this.onClickCommandUnpin = this.onClickCommandUnpin.bind(this);
            this.onClickedEditableText = this.onClickedEditableText.bind(this);
            this.onValidateEditableText = this.onValidateEditableText.bind(this);
        }

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.channelId}`;
        }

        /**
         * @private
         * @returns {string}
         */
        _computeAvatarUrl() {
            switch (this.channelType) {
                case 'channel':
                    return `/web/image/mail.channel/${this.channelId}/image_128`;
                case 'chat':
                    return this.channel.correspondent.avatarUrl;
            }
        }

        /**
         * @private
         * @returns {mail.thread}
         */
        _computeChannel() {
            return link(this.messaging.models['mail.thread'].findFromIdentifyingData({
                id: this.channelId,
                model: 'mail.channel',
            }));
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
                    return this.channel.localMessageUnreadCounter;
            }
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasLeaveCommand() {
            return this.channelType === 'channel' &&
                !this.channel.message_needaction_counter &&
                !this.channel.group_based_subscription;
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeHasRenameCommand() {
            return this.channelType === 'chat';
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
        _computeIsRenaming() {
            return this.messaging.discuss && this.hasRenameCommand && this.messaging.discuss.renamingThreads.includes(this.channel);
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
                case 'chat':
                    return true;
            }
        }

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @param {MouseEvent} ev
         */
        onCancelRenaming(ev) {
            this.messaging.discuss.cancelThreadRenaming(this.channel);
        }

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
            if (this.channel.creator === this.messaging.currentUser) {
                await this._askAdminConfirmation();
            }
            this.channel.unsubscribe();
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickCommandRename(ev) {
            ev.stopPropagation();
            this.messaging.discuss.setThreadRenaming(this.channel);
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
         * Stop propagation to prevent selecting this item.
         *
         * @param {CustomEvent} ev
         */
        onClickedEditableText(ev) {
            ev.stopPropagation();
        }

        /**
         * @param {CustomEvent} ev
         * @param {Object} ev.detail
         * @param {string} ev.detail.newName
         */
        onValidateEditableText(ev) {
            ev.stopPropagation();
            this.messaging.discuss.onValidateEditableText(this.channel, ev.detail.newName);
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
    }

    DiscussSidebarCategoryItem.fields = {
        /**
         * Image URL for the related channel thread.
         */
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
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
         * Boolean determines whether the item has a "rename" command.
         */
        hasRenameCommand: attr({
            compute: '_computeHasRenameCommand',
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
         * Boolean determines whether the item is currently being renamed.
         */
        isRenaming: attr({
            compute: '_computeIsRenaming',
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
            compute: '_computeChannel',
        }),
        /**
         * Id of the related channel thread.
         */
        channelId: attr({
            required: true,
        }),
        /**
         * Type of the related channel thread.
         */
        channelType: attr({
            related: 'channel.channel_type',
        }),

    };

    DiscussSidebarCategoryItem.modelName = 'mail.discuss_sidebar_category_item';

    return DiscussSidebarCategoryItem;
}

registerNewModel('mail.discuss_sidebar_category_item', factory);
