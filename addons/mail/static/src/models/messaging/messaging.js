/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';
import { insertAndReplace, link, unlink } from '@mail/model/model_field_command';
import { makeDeferred } from '@mail/utils/deferred/deferred';

const { EventBus } = owl;

registerModel({
    name: 'Messaging',
    identifyingFields: [],
    lifecycleHooks: {
        _willDelete() {
            if (this.env.services['bus_service']) {
                this.env.services['bus_service'].off('window_focus', null, this._handleGlobalWindowFocus);
            }
        },
    },
    recordMethods: {
        /**
         * Starts messaging and related records.
         */
        async start() {
            this.env.services['bus_service'].on('window_focus', null, this._handleGlobalWindowFocus);
            await this.initializer.start();
            if (!this.exists()) {
                return;
            }
            this.notificationHandler.start();
            this.update({ isInitialized: true });
            this.initializedPromise.resolve();
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
         * @returns {Thread|undefined}
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
         * Opens a chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} person forwarded to @see `getChat()`
         * @param {Object} [options] forwarded to @see `Thread:open()`
         * @returns {Thread|undefined}
         */
        async openChat(person, options) {
            const chat = await this.async(() => this.getChat(person));
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        },
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
            if (this.messaging.device.isMobile) {
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
                    channel = (await this.async(() =>
                        this.messaging.models['Thread'].performRpcChannelInfo({ ids: [id] })
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
            return this.messaging.openDocument({ id, model });
        },
        /**
         * Refreshes the value of `isNotificationPermissionDefault`.
         *
         * Must be called in flux-specific way because the browser does not
         * provide an API to detect when this value changes.
         */
        refreshIsNotificationPermissionDefault() {
            this.update({ isNotificationPermissionDefault: this._computeIsNotificationPermissionDefault() });
        },
        /**
         * @param {String} sessionId
         */
        toggleFocusedRtcSession(sessionId) {
            const rtcSession = this.messaging.models['RtcSession'].findFromIdentifyingData({
                id: sessionId,
            });
            const focusedSessionId = this.focusedRtcSession && this.focusedRtcSession.id;
            if (!sessionId || focusedSessionId === sessionId) {
                this.update({ focusedRtcSession: unlink() });
                return;
            }
            this.update({ focusedRtcSession: link(rtcSession) });
            if (this.userSetting.rtcLayout !== 'tiled') {
                return;
            }
            this.userSetting.update({ rtcLayout: 'sidebar' });
        },
        /**
         * @private
         * @returns {Object} browser
         */
        _computeBrowser() {
            return this.env.browser;
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
         * @returns {boolean}
         */
        _computeIsNotificationPermissionDefault() {
            const browserNotification = this.messaging.browser.Notification;
            return browserNotification ? browserNotification.permission === 'default' : false;
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
         */
        _onChangeRingingThreads() {
            if (this.ringingThreads && this.ringingThreads.length > 0) {
                this.soundEffects.incomingCall.play({ loop: true });
            } else {
                this.soundEffects.incomingCall.stop();
            }
        },
        /**
         * @private
         */
        _onChangeFocusedRtcSession() {
            this.rtc.filterIncomingVideoTraffic(this.focusedRtcSession && [this.focusedRtcSession.peerToken]);
        },
    },
    fields: {
        /**
         * Inverse of the messaging field present on all models. This field
         * therefore contains all existing records.
         */
        allRecords: many('Model', {
            inverse: 'messaging',
            isCausal: true,
        }),
        /**
         * Determines whether a loop should be started at initialization to
         * periodically fetch the im_status of all users.
         */
        autofetchPartnerImStatus: attr({
            default: true,
        }),
        browser: attr({
            compute: '_computeBrowser',
        }),
        cannedResponses: many('CannedResponse'),
        chatWindowManager: one('ChatWindowManager', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        commands: many('ChannelCommand'),
        companyName: attr(),
        currentGuest: one('Guest'),
        currentPartner: one('Partner'),
        currentUser: one('User'),
        device: one('Device', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        dialogManager: one('DialogManager', {
            default: insertAndReplace(),
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
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        focusedRtcSession: one('RtcSession'),
        /**
         * Mailbox History.
         */
        history: one('Thread'),
        /**
         * Mailbox Inbox.
         */
        inbox: one('Thread'),
        /**
         * Promise that will be resolved when messaging is initialized.
         */
        initializedPromise: attr({
            compute: '_computeInitializedPromise',
            required: true,
            readonly: true,
        }),
        initializer: one('MessagingInitializer', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        isCurrentUserGuest: attr({
            compute: '_computeIsCurrentUserGuest',
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
        /**
         * States whether the current environment is QUnit test. Useful to
         * disable some features that are not possible to test due to
         * technical limitations.
         */
        isQUnitTest: attr({
            default: false,
        }),
        locale: one('Locale', {
            default: insertAndReplace(),
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
            readonly: true,
            required: true,
        }),
        messagingMenu: one('MessagingMenu', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        notificationHandler: one('MessagingNotificationHandler', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        outOfFocusUnreadMessageCounter: attr({
            default: 0,
        }),
        partnerRoot: one('Partner'),
        /**
         * Determines which partners should be considered the public partners,
         * which are special partners notably used in livechat.
         */
        publicPartners: many('Partner'),
        /**
         * Threads for which the current partner has a pending invitation.
         * It is computed from the inverse relation for performance reasons.
         */
        ringingThreads: many('Thread', {
            inverse: 'messagingAsRingingThread',
        }),
        rtc: one('Rtc', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        soundEffects: one('SoundEffects', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
        }),
        /**
         * Mailbox Starred.
         */
        starred: one('Thread'),
        time: one('Time', {
            default: insertAndReplace(),
            isCausal: true,
            readonly: true,
            required: true,
        }),
        userSetting: one('UserSetting', {
            isCausal: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['ringingThreads'],
            methodName: '_onChangeRingingThreads',
        }),
        new OnChange({
            dependencies: ['focusedRtcSession'],
            methodName: '_onChangeFocusedRtcSession',
        }),
    ],
});
