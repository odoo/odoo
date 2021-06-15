/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2many, many2one, one2many, one2one } from '@mail/model/model_field';
import { create, replace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class Messaging extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            if (this.env.services['bus_service']) {
                this.env.services['bus_service'].off('window_focus', null, this._handleGlobalWindowFocus);
            }
            return super._willDelete(...arguments);
        }

        /**
         * Starts messaging and related records.
         */
        async start() {
            this._handleGlobalWindowFocus = this._handleGlobalWindowFocus.bind(this);
            this.env.services['bus_service'].on('window_focus', null, this._handleGlobalWindowFocus);
            await this.async(() => this.initializer.start());
            this.notificationHandler.start();
            this.update({ isInitialized: true });
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Open the form view of the record with provided id and model.
         * Gets the chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} param0
         * @param {integer} [param0.partnerId]
         * @param {integer} [param0.userId]
         * @param {Object} [options]
         * @returns {mail.thread|undefined}
         */
        async getChat({ partnerId, userId }) {
            if (userId) {
                const user = this.env.models['mail.user'].insert({ id: userId });
                return user.getChat();
            }
            if (partnerId) {
                const partner = this.env.models['mail.partner'].insert({ id: partnerId });
                return partner.getChat();
            }
        }

        /**
         * Opens a chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} person forwarded to @see `getChat()`
         * @param {Object} [options] forwarded to @see `mail.thread:open()`
         * @returns {mail.thread|undefined}
         */
        async openChat(person, options) {
            const chat = await this.async(() => this.getChat(person));
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        }

        /**
         * Opens the form view of the record with provided id and model.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         */
        async openDocument({ id, model }) {
            this.env.bus.trigger('do-action', {
                action: {
                    type: 'ir.actions.act_window',
                    res_model: model,
                    views: [[false, 'form']],
                    res_id: id,
                },
            });
            if (this.env.messaging.device.isMobile) {
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.env.messaging.messagingMenu.close();
            }
        }

        /**
         * Opens the most appropriate view that is a profile for provided id and
         * model.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         */
        async openProfile({ id, model }) {
            if (model === 'res.partner') {
                const partner = this.env.models['mail.partner'].insert({ id });
                return partner.openProfile();
            }
            if (model === 'res.users') {
                const user = this.env.models['mail.user'].insert({ id });
                return user.openProfile();
            }
            if (model === 'mail.channel') {
                let channel = this.env.models['mail.thread'].findFromIdentifyingData({ id, model: 'mail.channel' });
                if (!channel) {
                    channel = (await this.async(() =>
                        this.env.models['mail.thread'].performRpcChannelInfo({ ids: [id] })
                    ))[0];
                }
                if (!channel) {
                    this.env.services['notification'].notify({
                        message: this.env._t("You can only open the profile of existing channels."),
                        type: 'warning',
                    });
                    return;
                }
                return channel.openProfile();
            }
            return this.env.messaging.openDocument({ id, model });
        }

        /**
         * Refreshes the value of `isNotificationPermissionDefault`.
         *
         * Must be called in flux-specific way because the browser does not
         * provide an API to detect when this value changes.
         */
        refreshIsNotificationPermissionDefault() {
            this.update({ isNotificationPermissionDefault: this._computeIsNotificationPermissionDefault() });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _computeAllChannels() {
            return replace(this.allThreads.filter(thread => thread.model === 'mail.channel'));
        }

        /**
         * @private
         */
        _computeAllPinnedChannels() {
            return replace(this.allChannels.filter(channel => channel.isPinned));
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsNotificationPermissionDefault() {
            const browserNotification = this.env.browser.Notification;
            return browserNotification ? browserNotification.permission === 'default' : false;
        }

        /**
         * @private
         */
        _handleGlobalWindowFocus() {
            this.update({ outOfFocusUnreadMessageCounter: 0 });
            this.env.bus.trigger('set_title_part', {
                part: '_chat',
            });
        }

    }

    Messaging.fields = {
        /**
         * States all known channels.
         */
        allChannels: one2many('mail.thread', {
            compute: '_computeAllChannels',
            dependencies: [
                'allThreads',
                'allThreadsModel',
            ],
            readonly: true,
        }),
        /**
         * Serves as compute dependency.
         */
        allChannelsIsPinned: attr({
            related: 'allChannels.isPinned',
        }),
        /**
         * States all known pinned channels.
         */
        allPinnedChannels: one2many('mail.thread', {
            compute: '_computeAllPinnedChannels',
            dependencies: [
                'allChannels',
                'allChannelsIsPinned',
            ],
            readonly: true,
        }),
        /**
         * States all known threads.
         */
        allThreads: one2many('mail.thread', {
            inverse: 'messaging',
            readonly: true,
        }),
        /**
         * Serves as compute dependency.
         */
        allThreadsModel: attr({
            related: 'allThreads.model',
        }),
        cannedResponses: one2many('mail.canned_response'),
        chatWindowManager: one2one('mail.chat_window_manager', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        commands: one2many('mail.channel_command'),
        currentPartner: one2one('mail.partner'),
        currentUser: one2one('mail.user'),
        device: one2one('mail.device', {
            default: create(),
            isCausal: true,
            readonly: true,
        }),
        dialogManager: one2one('mail.dialog_manager', {
            default: create(),
            isCausal: true,
            readonly: true,
        }),
        discuss: one2one('mail.discuss', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Mailbox History.
         */
        history: one2one('mail.thread'),
        /**
         * Mailbox Inbox.
         */
        inbox: one2one('mail.thread'),
        initializer: one2one('mail.messaging_initializer', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        isInitialized: attr({
            default: false,
        }),
        /**
         * States whether browser Notification Permission is currently in its
         * 'default' state. This means it is allowed to make a request to the
         * user to enable notifications.
         */
        isNotificationPermissionDefault: attr({
            compute: '_computeIsNotificationPermissionDefault',
        }),
        locale: one2one('mail.locale', {
            default: create(),
            isCausal: true,
            readonly: true,
        }),
        messagingMenu: one2one('mail.messaging_menu', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        /**
         * Mailbox Moderation.
         */
        moderation: one2one('mail.thread'),
        notificationGroupManager: one2one('mail.notification_group_manager', {
            default: create(),
            isCausal: true,
            readonly: true,
        }),
        notificationHandler: one2one('mail.messaging_notification_handler', {
            default: create(),
            inverse: 'messaging',
            isCausal: true,
            readonly: true,
        }),
        outOfFocusUnreadMessageCounter: attr({
            default: 0,
        }),
        partnerRoot: many2one('mail.partner'),
        /**
         * Determines which partners should be considered the public partners,
         * which are special partners notably used in livechat.
         */
        publicPartners: many2many('mail.partner'),
        /**
         * Mailbox Starred.
         */
        starred: one2one('mail.thread'),
    };

    Messaging.modelName = 'mail.messaging';

    return Messaging;
}

registerNewModel('mail.messaging', factory);
