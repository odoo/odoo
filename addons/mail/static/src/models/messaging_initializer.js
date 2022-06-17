/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { executeGracefully } from '@mail/utils/utils';
import { link, insert, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'MessagingInitializer',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * @returns {Object}
         */
        async performInitRpc() {
            return await this.messaging.rpc({
                route: '/mail/init_messaging',
            }, { shadow: true });
        },
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
            const discuss = this.messaging.discuss;
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
            if (this.messaging.currentUser) {
                this.messaging.startFetchImStatus();
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
         * @param {integer} [param0.needaction_inbox_counter=0]
         * @param {Object} param0.partner_root
         * @param {Array[]} param0.publicPartners
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
            menu_id,
            needaction_inbox_counter = 0,
            partner_root,
            publicPartners,
            shortcodes = [],
            starred_counter = 0
        }) {
            const discuss = this.messaging.discuss;
            // partners first because the rest of the code relies on them
            this._initPartners({
                currentGuest,
                current_partner,
                current_user_id,
                partner_root,
            });
            this.messaging.update({ publicPartners });
            // mailboxes after partners and before other initializers that might
            // manipulate threads or messages
            this._initMailboxes({
                needaction_inbox_counter,
                starred_counter,
            });
            // init mail user settings
            if (current_user_settings) {
                this.messaging.models['res.users.settings'].insert(current_user_settings);
            }
            // various suggestions in no particular order
            this._initCannedResponses(shortcodes);
            // FIXME: guests should have (at least some) commands available
            if (!this.messaging.isCurrentUserGuest) {
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
         * @param {Object[]} mailFailuresData
         */
        async _initMailFailures(mailFailuresData) {
            await executeGracefully(mailFailuresData.map(messageData => () => {
                const message = this.messaging.models['Message'].insert(
                    this.messaging.models['Message'].convertData(messageData)
                );
                // implicit: failures are sent by the server at initialization
                // only if the current partner is author of the message
                if (!message.author && this.messaging.currentPartner) {
                    message.update({ author: replace(this.messaging.currentPartner) });
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
                this.messaging.update({ currentGuest: insert(currentGuest) });
            }
            if (current_partner) {
                const partnerData = this.messaging.models['Partner'].convertData(current_partner);
                this.messaging.update({
                    currentPartner: insert(partnerData),
                    currentUser: insert({ id: currentUserId }),
                });
            }
            if (partner_root) {
                this.messaging.update({
                    partnerRoot: insert(this.messaging.models['Partner'].convertData(partner_root)),
                });
            }
        },
        /**
         * @private
         */
        async _loadMessageFailures() {
            const data = await this.messaging.rpc({
                route: '/mail/load_message_failures',
            }, { shadow: true });
            this._initMailFailures(data);
        },
    },
});
