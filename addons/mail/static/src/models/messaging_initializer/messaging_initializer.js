/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { executeGracefully } from '@mail/utils/utils';
import { link, insert, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'MessagingInitializer',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * Fetch messaging data initially to populate the store specifically for
         * the current user. This includes pinned channels for instance.
         */
        async start() {
            this.messaging.update({
                history: insertAndReplace({
                    id: 'history',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("History"),
                }),
                inbox: insertAndReplace({
                    id: 'inbox',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("Inbox"),
                }),
                starred: insertAndReplace({
                    id: 'starred',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("Starred"),
                }),
            });
            this.messaging.device.start();
            if (this.env.session.uid) { // not guest
                this.messaging.update({
                    currentPartner: insertAndReplace({
                        id: this.env.session.partner_id,
                        name: this.env.session.name,
                        user: insertAndReplace({ id: this.env.session.uid }),
                    }),
                    currentUser: insertAndReplace({ id: this.env.session.uid }),
                });
            }
            if (this.messaging.autofetchPartnerImStatus) {
                this.messaging.models['Partner'].startLoopFetchImStatus();
            }
            const data = await this.env.services.rpc({
                route: '/mail/init_messaging',
            }, { shadow: true });
            if (!this.exists()) {
                return;
            }
            await this._init(data);
            if (!this.exists()) {
                return;
            }
            this.messaging.update({ isInitialized: true });
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Object[]} param0.channels
         * @param {Object} param0.currentGuest
         * @param {Object} param0.current_partner
         * @param {integer} param0.current_user_id
         * @param {Object} param0.current_user_settings
         * @param {Object} [param0.mail_failures={}]
         * @param {integer} [param0.needaction_inbox_counter=0]
         * @param {Object} param0.partner_root
         * @param {Object[]} param0.public_partners
         * @param {Object[]} [param0.shortcodes=[]]
         * @param {integer} [param0.starred_counter=0]
         */
        async _init({
            channels,
            commands = [],
            companyName,
            current_partner,
            currentGuest,
            current_user_id,
            current_user_settings,
            mail_failures = {},
            menu_id,
            needaction_inbox_counter = 0,
            partner_root,
            public_partners,
            shortcodes = [],
            starred_counter = 0
        }) {
            this._initPartners({
                currentGuest,
                current_partner,
                current_user_id,
                partner_root,
                public_partners,
            });
            this._initMailboxes({
                needaction_inbox_counter,
                starred_counter,
            });
            if (current_user_settings) {
                this._initResUsersSettings(current_user_settings);
            }
            this._initCannedResponses(shortcodes);
            if (this.messaging.currentUser) {
                this._initCommands();
            }
            this._initChannels(channels);
            this._initMailFailures(mail_failures);
            this.messaging.discuss.update({ menu_id });
            this.messaging.update({ companyName });
        },
        /**
         * @private
         * @param {Object[]} cannedResponsesData
         */
        _initCannedResponses(cannedResponsesData) {
            this.messaging.update({
                cannedResponses: insert(cannedResponsesData),
            });
        },
        /**
         * @private
         * @param {Object[]} channelsData
         */
        async _initChannels(channelsData) {
            return executeGracefully(channelsData.map(channelData => () => {
                const convertedData = this.messaging.models['Thread'].convertData(channelData);
                if (!convertedData.members) {
                    // channel_info does not return all members of channel for
                    // performance reasons, but code is expecting to know at
                    // least if the current partner is member of it.
                    // (e.g. to know when to display "invited" notification)
                    // Current partner can always be assumed to be a member of
                    // channels received at init.
                    if (this.messaging.currentPartner) {
                        convertedData.members = link(this.messaging.currentPartner);
                    }
                    if (this.messaging.currentGuest) {
                        convertedData.guestMembers = link(this.messaging.currentGuest);
                    }
                }
                const channel = this.messaging.models['Thread'].insert(
                    Object.assign({ model: 'mail.channel' }, convertedData)
                );
                // flux specific: channels received at init have to be
                // considered pinned. task-2284357
                if (!channel.isPinned) {
                    channel.pin();
                }
            }));
        },
        /**
         * @private
         */
        _initCommands() {
            this.messaging.update({
                commands: insert([
                    {
                        help: this.env._t("Show a helper message"),
                        methodName: 'execute_command_help',
                        name: "help",
                    },
                    {
                        help: this.env._t("Leave this channel"),
                        methodName: 'execute_command_leave',
                        name: "leave",
                    },
                    {
                        channel_types: ['channel', 'chat'],
                        help: this.env._t("List users in the current channel"),
                        methodName: 'execute_command_who',
                        name: "who",
                    }
                ]),
            });
        },
        /**
         * @private
         * @param {Object} param0
         * @param {integer} param0.needaction_inbox_counter
         * @param {integer} param0.starred_counter
         */
        _initMailboxes({
            needaction_inbox_counter,
            starred_counter,
        }) {
            this.messaging.inbox.update({ counter: needaction_inbox_counter });
            this.messaging.starred.update({ counter: starred_counter });
        },
        /**
         * @private
         * @param {Object} mailFailuresData
         */
        async _initMailFailures(mailFailuresData) {
            await executeGracefully(mailFailuresData.map(messageData => () => {
                const message = this.messaging.models['Message'].insert(
                    this.messaging.models['Message'].convertData(messageData)
                );
                // implicit: failures are sent by the server at initialization
                // only if the current partner is author of the message
                if (!message.author && this.messaging.currentPartner) {
                    message.update({ author: link(this.messaging.currentPartner) });
                }
            }));
        },
        /**
         * @param {object} resUsersSettings
         * @param {integer} resUsersSettings.id
         * @param {boolean} resUsersSettings.is_discuss_sidebar_category_channel_open
         * @param {boolean} resUsersSettings.is_discuss_sidebar_category_chat_open
         * @param {boolean} resUsersSettings.use_push_to_talk
         * @param {String} resUsersSettings.push_to_talk_key
         * @param {number} resUsersSettings.voice_active_duration
         * @param {Object} [resUsersSettings.volume_settings]
         */
        _initResUsersSettings({
            id,
            is_discuss_sidebar_category_channel_open,
            is_discuss_sidebar_category_chat_open,
            use_push_to_talk,
            push_to_talk_key,
            voice_active_duration,
            volume_settings = [],
        }) {
            this.messaging.currentUser.update({ resUsersSettingsId: id });
            this.messaging.update({
                userSetting: insertAndReplace({
                    id,
                    usePushToTalk: use_push_to_talk,
                    pushToTalkKey: push_to_talk_key,
                    voiceActiveDuration: voice_active_duration,
                    volumeSettings: volume_settings,
                }),
            });
            this.messaging.discuss.categoryChannel.update({ isServerOpen: is_discuss_sidebar_category_channel_open });
            this.messaging.discuss.categoryChat.update({ isServerOpen: is_discuss_sidebar_category_chat_open });
        },
        /**
         * @private
         * @param {Object} currentGuest
         * @param {Object} current_partner
         * @param {integer} current_user_id
         * @param {Object} partner_root
         * @param {Object[]} [public_partners=[]]
         */
        _initPartners({
            currentGuest,
            current_partner,
            current_user_id: currentUserId,
            partner_root,
            public_partners = [],
        }) {
            if (currentGuest) {
                this.messaging.update({ currentGuest: insert(currentGuest) });
                if (this.messaging.discussPublicView && this.messaging.discussPublicView.welcomeView) {
                    this.messaging.discussPublicView.welcomeView.update({ pendingGuestName: this.messaging.currentGuest.name });
                }
            }
            if (current_partner) {
                const partnerData = this.messaging.models['Partner'].convertData(current_partner);
                partnerData.user = insert({ id: currentUserId });
                this.messaging.update({
                    currentPartner: insert(partnerData),
                    currentUser: insert({ id: currentUserId }),
                });
            }
            this.messaging.update({
                partnerRoot: insert(this.messaging.models['Partner'].convertData(partner_root)),
                publicPartners: insert(public_partners.map(
                    publicPartner => this.messaging.models['Partner'].convertData(publicPartner)
                )),
            });
        },
    },
});
