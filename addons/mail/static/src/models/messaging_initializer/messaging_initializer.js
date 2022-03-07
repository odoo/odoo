/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { executeGracefully } from '@mail/utils/utils';
import { link, insert, insertAndReplace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class MessagingInitializer extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

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
            const device = this.messaging.device;
            device.start();
            const data = await this.async(() => this.env.services.rpc({
                route: '/mail/init_messaging',
            }, { shadow: true }));
            await this.async(() => this._init(data));
            if (this.messaging.autofetchPartnerImStatus) {
                this.messaging.models['mail.partner'].startLoopFetchImStatus();
            }
            if (this.messaging.currentUser) {
                this._loadMessageFailures();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Object} param0
         * @param {Object[]} param0.channels
         * @param {Object} param0.currentGuest
         * @param {Object} param0.current_partner
         * @param {integer} param0.current_user_id
         * @param {Object} param0.current_user_settings
         * @param {Object} [param0.mail_failures=[]]
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
            mail_failures = [],
            menu_id,
            needaction_inbox_counter = 0,
            partner_root,
            public_partners,
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
                public_partners,
            });
            // mailboxes after partners and before other initializers that might
            // manipulate threads or messages
            this._initMailboxes({
                needaction_inbox_counter,
                starred_counter,
            });
            // init mail user settings
            if (current_user_settings) {
                this._initResUsersSettings(current_user_settings);
            } else {
                this.messaging.update({
                    userSetting: insertAndReplace({
                        id: -1, // fake id for guest
                    }),
                });
            }
            // various suggestions in no particular order
            this._initCannedResponses(shortcodes);
            // FIXME: guests should have (at least some) commands available
            if (!this.messaging.isCurrentUserGuest) {
                this._initCommands();
            }
            // channels when the rest of messaging is ready
            await this.async(() => this._initChannels(channels));
            // failures after channels
            this._initMailFailures(mail_failures);
            discuss.update({ menu_id });
            // company related data
            this.messaging.update({ companyName });
        }

        /**
         * @private
         * @param {Object[]} cannedResponsesData
         */
        _initCannedResponses(cannedResponsesData) {
            this.messaging.update({
                cannedResponses: insert(cannedResponsesData),
            });
        }

        /**
         * @private
         * @param {Object[]} channelsData
         */
        async _initChannels(channelsData) {
            return executeGracefully(channelsData.map(channelData => () => {
                const convertedData = this.messaging.models['mail.thread'].convertData(channelData);
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
                const channel = this.messaging.models['mail.thread'].insert(
                    Object.assign({ model: 'mail.channel' }, convertedData)
                );
                // flux specific: channels received at init have to be
                // considered pinned. task-2284357
                if (!channel.isPinned) {
                    channel.pin();
                }
            }));
        }

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
        }

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
        }

        /**
         * @private
         * @param {Object[]} mailFailuresData
         */
        async _initMailFailures(mailFailuresData) {
            await executeGracefully(mailFailuresData.map(messageData => () => {
                const message = this.messaging.models['mail.message'].insert(
                    this.messaging.models['mail.message'].convertData(messageData)
                );
                // implicit: failures are sent by the server at initialization
                // only if the current partner is author of the message
                if (!message.author && this.messaging.currentPartner) {
                    message.update({ author: link(this.messaging.currentPartner) });
                }
            }));
            this.messaging.notificationGroupManager.computeGroups();
        }

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
            this.messaging.discuss.update({
                categoryChannel: insertAndReplace({
                    autocompleteMethod: 'channel',
                    commandAddTitleText: this.env._t("Add or join a channel"),
                    hasAddCommand: true,
                    hasViewCommand: true,
                    isServerOpen: is_discuss_sidebar_category_channel_open,
                    name: this.env._t("Channels"),
                    newItemPlaceholderText: this.env._t("Find or create a channel..."),
                    serverStateKey: 'is_discuss_sidebar_category_channel_open',
                    sortComputeMethod: 'name',
                    supportedChannelTypes: ['channel'],
                }),
                categoryChat: insertAndReplace({
                    autocompleteMethod: 'chat',
                    commandAddTitleText: this.env._t("Start a conversation"),
                    hasAddCommand: true,
                    isServerOpen: is_discuss_sidebar_category_chat_open,
                    name: this.env._t("Direct Messages"),
                    newItemPlaceholderText: this.env._t("Find or start a conversation..."),
                    serverStateKey: 'is_discuss_sidebar_category_chat_open',
                    sortComputeMethod: 'last_action',
                    supportedChannelTypes: ['chat', 'group'],
                }),
            });
        }

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
            }
            if (current_partner) {
                const partnerData = this.messaging.models['mail.partner'].convertData(current_partner);
                partnerData.user = insert({ id: currentUserId });
                this.messaging.update({
                    currentPartner: insert(partnerData),
                    currentUser: insert({ id: currentUserId }),
                });
            }
            this.messaging.update({
                partnerRoot: insert(this.messaging.models['mail.partner'].convertData(partner_root)),
                publicPartners: insert(public_partners.map(
                    publicPartner => this.messaging.models['mail.partner'].convertData(publicPartner)
                )),
            });
        }

        /**
         * @private
         */
        async _loadMessageFailures() {
            const data = await this.env.services.rpc({
                route: '/mail/load_message_failures',
            }, { shadow: true });
            this._initMailFailures(data);
        }

    }
    MessagingInitializer.identifyingFields = ['messaging'];
    MessagingInitializer.modelName = 'mail.messaging_initializer';

    return MessagingInitializer;
}

registerNewModel('mail.messaging_initializer', factory);
