/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { executeGracefully } from '@mail/utils/utils';
import { create, link, insert } from '@mail/model/model_field_command';


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
                history: create({
                    id: 'history',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("History"),
                }),
                inbox: create({
                    id: 'inbox',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("Inbox"),
                }),
                starred: create({
                    id: 'starred',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("Starred"),
                }),
            });
            const device = this.messaging.device;
            device.start();
            const discuss = this.messaging.discuss;
            const data = await this.env.services.rpc('/mail/init_messaging', {}, { silent: true });
            if (!this.exists()) {
                return;
            }
            await this._init(data);
            if (!this.exists()) {
                return;
            }
            if (discuss.isOpen) {
                discuss.openInitThread();
            }
            if (this.messaging.autofetchPartnerImStatus) {
                this.messaging.models['mail.partner'].startLoopFetchImStatus();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Object} param0
         * @param {Object[]} param0.channels
         * @param {Object} param0.current_partner
         * @param {integer} param0.current_user_id
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
            current_partner,
            current_user_id,
            mail_failures = {},
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
            // various suggestions in no particular order
            this._initCannedResponses(shortcodes);
            this._initCommands();
            // channels when the rest of messaging is ready
            await this.async(() => this._initChannels(channels));
            // failures after channels
            this._initMailFailures(mail_failures);
            discuss.update({ menu_id });
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
                    convertedData.members = link(this.messaging.currentPartner);
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
         * @param {Object} mailFailuresData
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
         * @private
         * @param {Object} current_partner
         * @param {integer} current_user_id
         * @param {Object} partner_root
         * @param {Object[]} [public_partners=[]]
         */
        _initPartners({
            current_partner,
            current_user_id: currentUserId,
            partner_root,
            public_partners = [],
        }) {
            this.messaging.update({
                currentPartner: insert(Object.assign(
                    this.messaging.models['mail.partner'].convertData(current_partner),
                    {
                        user: insert({ id: currentUserId }),
                    }
                )),
                currentUser: insert({ id: currentUserId }),
                partnerRoot: insert(this.messaging.models['mail.partner'].convertData(partner_root)),
                publicPartners: insert(public_partners.map(
                    publicPartner => this.messaging.models['mail.partner'].convertData(publicPartner)
                ))
            });
        }

    }

    MessagingInitializer.modelName = 'mail.messaging_initializer';

    return MessagingInitializer;
}

registerNewModel('mail.messaging_initializer', factory);
