/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred';

import { browser } from '@web/core/browser/browser';

const { EventBus } = owl;

registerModel({
    name: 'Messaging',
    lifecycleHooks: {
        _created() {
            odoo.__DEBUG__.messaging = this;
            this.refreshIsNotificationPermissionDefault();
        },
        _willDelete() {
            this.env.bus.removeEventListener('window_focus', this._handleGlobalWindowFocus);
            delete odoo.__DEBUG__.messaging;
        },
    },
    recordMethods: {
        /**
         * Starts messaging and related records.
         */
        async start() {
            this.env.bus.addEventListener('window_focus', this._handleGlobalWindowFocus);
            await this.initializer.start();
            if (!this.exists()) {
                return;
            }
            if (this.notificationHandler) {
                this.notificationHandler.start();
            }
            this.update({ isInitialized: true });
            this.initializedPromise.resolve();
        },
        /**
         * Executes the provided functions in order, but with a potential delay between
         * them if they take too much time. This is done in order to avoid blocking the
         * main thread for too long.
         *
         * @param {function[]} functions
         */
        async executeGracefully(functions) {
            let date = new Date();
            for (const func of functions) {
                if (new Date() - date > 100) {
                    await new Promise(resolve => setTimeout(resolve, this.isInQUnitTest ? 0 : 50));
                    date = new Date();
                }
                await func();
            }
        },
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
         * @returns {Channel|undefined}
         */
        async getChat({ partnerId, userId }) {
            if (userId) {
                const user = this.messaging.models['User'].insert({ id: userId });
                return user.getChat();
            }
            if (partnerId) {
                const partner = this.messaging.models['Partner'].insert({ id: partnerId });
                return partner.getChat();
            }
        },
        /**
         * Display a notification to the user.
         *
         * @param {Object} params
         * @param {string} [params.message]
         * @param {string} [params.subtitle]
         * @param {Object[]} [params.buttons]
         * @param {boolean} [params.sticky]
         * @param {string} [params.type]
         * @param {string} [params.className]
         * @param {function} [params.onClose]
         * @return {number} the id of the notification.
         */
        notify(params) {
            const { message, ...options } = params;
            return this.env.services.notification.add(message, options);
        },
        onFetchImStatusTimerTimeout() {
            this.startFetchImStatus();
        },
        /**
         * Opens a chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} person forwarded to @see `getChat()`
         * @param {Object} [options] forwarded to @see `Thread:open()`
         */
        async openChat(person, options) {
            const chat = await this.getChat(person);
            if (!this.exists() || !chat) {
                return;
            }
            await chat.thread.open(options);
            if (!this.exists()) {
                return;
            }
        },
        /**
         * Opens the form view of the record with provided id and model.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         */
        async openDocument({ id, model }) {
            this.env.services.action.doAction({
                type: 'ir.actions.act_window',
                res_model: model,
                views: [[false, 'form']],
                res_id: id,
            });
            if (this.messaging.device.isSmall) {
                // When opening documents chat windows need to be closed
                this.messaging.chatWindowManager.closeAll();
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.messaging.messagingMenu.close();
            }
        },
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
                const partner = this.messaging.models['Partner'].insert({ id });
                return partner.openProfile();
            }
            if (model === 'res.users') {
                const user = this.messaging.models['User'].insert({ id });
                return user.openProfile();
            }
            if (model === 'mail.channel') {
                let channel = this.messaging.models['Thread'].findFromIdentifyingData({ id, model: 'mail.channel' });
                if (!channel) {
                    const res = await this.messaging.models['Thread'].performRpcChannelInfo({ ids: [id] });
                    if (!this.exists()) {
                        return;
                    }
                    channel = res[0];
                }
                if (!channel) {
                    this.messaging.notify({
                        message: this.env._t("You can only open the profile of existing channels."),
                        type: 'warning',
                    });
                    return;
                }
                return channel.openProfile();
            }
            return this.messaging.openDocument({ id, model });
        },
        /**
         * Perform a rpc call and return a promise resolving to the result.
         *
         * @param {Object} params
         * @return {any}
         */
        async rpc(params, options = {}) {
            if (params.route) {
                const { route, params: rpcParameters } = params;
                const { shadow: silent, ...rpcSettings } = options;
                return this.env.services.rpc(route, rpcParameters, { silent, ...rpcSettings });
            } else {
                const { args, method, model, kwargs = {} } = params;
                const { domain, fields, groupBy } = kwargs;

                const ormService = 'shadow' in options ? this.env.services.orm.silent : this.env.services.orm;
                switch (method) {
                    case 'create':
                        return ormService.create(model, args[0], kwargs);
                    case 'read':
                        return ormService.read(model, args[0], args.length > 1 ? args[1] : undefined, kwargs);
                    case 'read_group':
                        return ormService.readGroup(model, domain, fields, groupBy, kwargs);
                    case 'search':
                        return ormService.search(model, args[0], kwargs);
                    case 'search_read':
                        return ormService.searchRead(model, domain, fields, kwargs);
                    case 'unlink':
                        return ormService.unlink(model, args[0], kwargs);
                    case 'write':
                        return ormService.write(model, args[0], args[1], kwargs);
                    default:
                        return ormService.call(model, method, args, kwargs);
                }
            }
        },
        /**
         * Refreshes the value of `isNotificationPermissionDefault`.
         *
         * Must be called in flux-specific way because the browser does not
         * provide an API to detect when this value changes.
         */
        refreshIsNotificationPermissionDefault() {
            const browserNotification = this.messaging.browser.Notification;
            this.update({
                isNotificationPermissionDefault: Boolean(browserNotification) && browserNotification.permission === 'default',
            });
        },
        async startFetchImStatus() {
            this.update({
                fetchImStatusTimer: { doReset: this.fetchImStatusTimer ? true : undefined },
            });
            const partnerIds = [];
            for (const partner of this.models['Partner'].all()) {
                if (partner.im_status !== 'im_partner' && !partner.is_public) {
                    partnerIds.push(partner.id);
                }
            }
            if (partnerIds.length === 0) {
                return;
            }
            const guestIds = [];
            for (const guest of this.models['Guest'].all()) {
                guestIds.push(guest.id);
            }
            if (partnerIds.length !== 0 || guestIds.length !== 0) {
                const dataList = await this.messaging.rpc({
                    route: '/bus/im_status',
                    params: {
                        partner_ids: partnerIds,
                        guest_ids: guestIds,
                    },
                }, { shadow: true });
                this.models['Partner'].insert(dataList.partners);
                if (dataList.guests) {
                    this.models['Guest'].insert(dataList.guests);
                }
            }
        },
        /**
         * @private
         * @returns {Object} browser
         */
        _computeBrowser() {
            return browser;
        },
        /**
         * @private
         * @returns {Promise}
         */
        _computeInitializedPromise() {
            return makeDeferred();
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsCurrentUserGuest() {
            return Boolean(!this.currentPartner && this.currentGuest);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsNotificationBlocked() {
            const windowNotification = this.browser.Notification;
            return (
                windowNotification &&
                windowNotification.permission !== 'granted' &&
                !this.isNotificationPermissionDefault
            );
        },
        /**
         * @private
         * @returns {EventBus}
         */
        _computeMessagingBus() {
            if (this.messagingBus) {
                return; // avoid overwrite if already provided (example in tests)
            }
            return new EventBus();
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeCallInviteRequestPopups() {
            if (this.ringingThreads.length === 0) {
                return clear();
            }
            return this.ringingThreads.map(thread => thread.callInviteRequestPopup);
        },
        /**
         * @private
         */
        _handleGlobalWindowFocus() {
            this.update({ outOfFocusUnreadMessageCounter: 0 });
            this.env.bus.trigger('set_title_part', {
                part: '_chat',
            });
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeNotificationHandler() {
            return {};
        },
        /**
         * @private
         */
        _onChangeAllCurrentClientThreads() {
            if (this.isInitialized) {
                this.env.services.bus_service.forceUpdateChannels();
            }
        },
        /**
         * @private
         */
        _onChangeRingingThreads() {
            if (this.ringingThreads && this.ringingThreads.length > 0) {
                this.soundEffects.incomingCall.play({ loop: true });
            } else {
                this.soundEffects.incomingCall.stop();
            }
        },
    },
    fields: {
        allMailboxes: many('Mailbox', {
            inverse: 'messagingAsAnyMailbox',
        }),
        /**
         * Inverse of the messaging field present on all models. This field
         * therefore contains all existing records.
         */
        allRecords: many('Record', {
            inverse: 'messaging',
            isCausal: true,
        }),
        /**
         * This field contains all current client channels.
         */
        allCurrentClientThreads: many('Thread', {
            inverse: 'messagingAsAllCurrentClientThreads',
        }),
        browser: attr({
            compute: '_computeBrowser',
        }),
        cannedResponses: many('CannedResponse'),
        chatWindowManager: one('ChatWindowManager', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines which message view is currently clicked, if any.
         */
        clickedMessageView: one('MessageView', {
            inverse: 'messagingAsClickedMessageView',
        }),
        commands: many('ChannelCommand'),
        companyName: attr(),
        currentGuest: one('Guest'),
        currentPartner: one('Partner'),
        currentUser: one('User'),
        device: one('Device', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        dialogManager: one('DialogManager', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines whether animations should be disabled.
         */
        disableAnimation: attr({
            default: false,
        }),
        discuss: one('Discuss', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        emojiRegistry: one('EmojiRegistry', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        fetchImStatusTimer: one('Timer', {
            inverse: 'messagingOwnerAsFetchImStatusTimer',
        }),
        fetchImStatusTimerDuration: attr({
            default: 50 * 1000,
        }),
        hasLinkPreviewFeature: attr(),
        history: one('Mailbox', {
            default: {},
            inverse: 'messagingAsHistory',
        }),
        inbox: one('Mailbox', {
            default: {},
            inverse: 'messagingAsInbox',
        }),
        /**
         * Promise that will be resolved when messaging is initialized.
         */
        initializedPromise: attr({
            compute: '_computeInitializedPromise',
            required: true,
        }),
        initializer: one('MessagingInitializer', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        internalUserGroupId: attr(),
        isCurrentUserGuest: attr({
            compute: '_computeIsCurrentUserGuest',
        }),
        isInitialized: attr({
            default: false,
        }),
        isInQUnitTest: attr({
            default: false,
        }),
        isNotificationBlocked: attr({
            compute: '_computeIsNotificationBlocked',
        }),
        /**
         * States whether browser Notification Permission is currently in its
         * 'default' state. This means it is allowed to make a request to the
         * user to enable notifications.
         */
        isNotificationPermissionDefault: attr(),
        locale: one('Locale', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines after how much time in ms a "loading" indicator should be
         * shown. Useful to avoid flicker for almost instant loading.
         */
        loadingBaseDelayDuration: attr({
            default: 400,
        }),
        /**
         * Determines the bus that is used to communicate messaging events.
         */
        messagingBus: attr({
            compute: '_computeMessagingBus',
            required: true,
        }),
        messagingMenu: one('MessagingMenu', {
            default: {},
            isCausal: true,
        }),
        notificationHandler: one('MessagingNotificationHandler', {
            compute: '_computeNotificationHandler',
            isCausal: true,
        }),
        outOfFocusUnreadMessageCounter: attr({
            default: 0,
        }),
        partnerRoot: one('Partner'),
        popoverManager: one('PopoverManager', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        /**
         * Threads for which the current partner has a pending invitation.
         * It is computed from the inverse relation for performance reasons.
         */
        ringingThreads: many('Thread', {
            inverse: 'messagingAsRingingThread',
        }),
        rtc: one('Rtc', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        callInviteRequestPopups: many('CallInviteRequestPopup', {
            compute: '_computeCallInviteRequestPopups',
            isCausal: true,
        }),
        soundEffects: one('SoundEffects', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        starred: one('Mailbox', {
            default: {},
            inverse: 'messagingAsStarred',
        }),
        userNotificationManager: one('UserNotificationManager', {
            default: {},
            isCausal: true,
            readonly: true,
        }),
        userSetting: one('UserSetting', {
            default: {},
            isCausal: true,
        }),
    },
    onChanges: [
        {
            dependencies: ['ringingThreads'],
            methodName: '_onChangeRingingThreads',
        },
        {
            dependencies: ['allCurrentClientThreads'],
            methodName: '_onChangeAllCurrentClientThreads',
        },
    ],
});
