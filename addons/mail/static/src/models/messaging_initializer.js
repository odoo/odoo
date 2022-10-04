/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { insert } from '@mail/model/model_field_command';

registerModel({
    name: 'MessagingInitializer',
    recordMethods: {
        /**
         * @returns {Object}
         */
        async performInitRpc() {
            return await this.global.Messaging.rpc({
                route: '/mail/init_messaging',
            }, { shadow: true });
        },
        /**
         * Fetch messaging data initially to populate the store specifically for
         * the current user. This includes pinned channels for instance.
         */
        async start() {
            this.global.Device.start();
            const discuss = this.global.Discuss;
            const data = await this.performInitRpc();
            if (!this.exists()) {
                return;
            }
            await this._init(data);
            if (!this.exists()) {
                return;
            }
            if (discuss.discussView) {
                discuss.openInitThread();
            }
            if (this.global.Messaging.currentUser) {
                this.global.Messaging.updateImStatusRegistration();
                this._loadMessageFailures();
            }
        },
        /**
         * @private
         * @param {Object} param0
         * @param {Object[]} param0.channels
         * @param {Object} param0.currentGuest
         * @param {Object} param0.current_partner
         * @param {integer} param0.current_user_id
         * @param {Object} param0.current_user_settings
         * @param {boolean} [param0.hasLinkPreviewFeature]
         * @param {integer} [param0.internalUserGroupId]
         * @param {integer} [param0.needaction_inbox_counter=0]
         * @param {Object} param0.partner_root
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
            hasLinkPreviewFeature,
            internalUserGroupId,
            menu_id,
            needaction_inbox_counter = 0,
            partner_root,
            shortcodes = [],
            starred_counter = 0,
        }) {
            const discuss = this.global.Discuss;
            // partners first because the rest of the code relies on them
            this._initPartners({
                currentGuest,
                current_partner,
                current_user_id,
                partner_root,
            });
            // mailboxes after partners and before other initializers that might
            // manipulate threads or messages
            this._initMailboxes({
                needaction_inbox_counter,
                starred_counter,
            });
            // init mail user settings
            if (current_user_settings) {
                this.global.Messaging.models['res.users.settings'].insert(current_user_settings);
            }
            // various suggestions in no particular order
            this._initCannedResponses(shortcodes);
            // FIXME: guests should have (at least some) commands available
            if (!this.global.Messaging.isCurrentUserGuest) {
                this._initCommands();
            }
            // channels when the rest of messaging is ready
            if (channels) {
                await this._initChannels(channels);
            }
            if (!this.exists()) {
                return;
            }
            discuss.update({ menu_id });
            // company related data
            this.global.Messaging.update({ companyName, hasLinkPreviewFeature, internalUserGroupId });
        },
        /**
         * @private
         * @param {Object[]} cannedResponsesData
         */
        _initCannedResponses(cannedResponsesData) {
            this.global.Messaging.update({
                cannedResponses: insert(cannedResponsesData),
            });
        },
        /**
         * @private
         * @param {Object[]} channelsData
         */
        async _initChannels(channelsData) {
            return this.global.Messaging.executeGracefully(channelsData.map(channelData => () => {
                if (!this.exists()) {
                    return;
                }
                const convertedData = this.global.Messaging.models['Thread'].convertData(channelData);
                const channel = this.global.Messaging.models['Thread'].insert(
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
            this.global.Messaging.update({
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
                        channel_types: ['channel', 'chat', 'group'],
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
            this.global.Messaging.inbox.update({ counter: needaction_inbox_counter });
            this.global.Messaging.starred.update({ counter: starred_counter });
        },
        /**
         * @private
         * @param {Object[]} mailFailuresData
         */
        async _initMailFailures(mailFailuresData) {
            await this.global.Messaging.executeGracefully(mailFailuresData.map(messageData => () => {
                if (!this.exists()) {
                    return;
                }
                const message = this.global.Messaging.models['Message'].insert(
                    this.global.Messaging.models['Message'].convertData(messageData)
                );
                // implicit: failures are sent by the server at initialization
                // only if the current partner is author of the message
                if (!message.author && this.global.Messaging.currentPartner) {
                    message.update({ author: this.global.Messaging.currentPartner });
                }
            }));
        },
        /**
         * @private
         * @param {Object} currentGuest
         * @param {Object} current_partner
         * @param {integer} current_user_id
         * @param {Object} partner_root
         */
        _initPartners({
            currentGuest,
            current_partner,
            current_user_id: currentUserId,
            partner_root,
        }) {
            if (currentGuest) {
                this.global.Messaging.update({ currentGuest: insert(currentGuest) });
            }
            if (current_partner) {
                this.global.Messaging.update({
                    currentPartner: current_partner,
                    currentUser: insert({ id: currentUserId }),
                });
            }
            if (partner_root) {
                this.global.Messaging.update({
                    partnerRoot: partner_root,
                });
            }
        },
        /**
         * @private
         */
        async _loadMessageFailures() {
            const data = await this.global.Messaging.rpc({
                route: '/mail/load_message_failures',
            }, { shadow: true });
            this._initMailFailures(data);
        },
    },
});
