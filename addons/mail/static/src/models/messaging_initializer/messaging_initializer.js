/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
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
            const context = Object.assign({
                isMobile: device.isMobile,
            }, this.env.session.user_context);
            const discuss = this.messaging.discuss;
            const data = await this.async(() => this.env.services.rpc({
                route: '/mail/init_messaging',
                params: { context: context }
            }, { shadow: true }));
            await this.async(() => this._init(data));
            if (discuss.isOpen) {
                discuss.openInitThread();
            }
            if (this.env.autofetchPartnerImStatus) {
                this.env.models['mail.partner'].startLoopFetchImStatus();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {Object} param0
         * @param {Object} param0.channel_slots
         * @param {Array} [param0.commands=[]]
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
            channel_slots,
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
            this._initCommands(commands);
            // channels when the rest of messaging is ready
            await this.async(() => this._initChannels(channel_slots));
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
         * @param {Object} [param0={}]
         * @param {Object[]} [param0.channel_channel=[]]
         * @param {Object[]} [param0.channel_direct_message=[]]
         * @param {Object[]} [param0.channel_private_group=[]]
         */
        async _initChannels({
            channel_channel = [],
            channel_direct_message = [],
            channel_private_group = [],
        } = {}) {
            const channelsData = channel_channel.concat(channel_direct_message, channel_private_group);
            return executeGracefully(channelsData.map(channelData => () => {
                const convertedData = this.env.models['mail.thread'].convertData(channelData);
                if (!convertedData.members) {
                    // channel_info does not return all members of channel for
                    // performance reasons, but code is expecting to know at
                    // least if the current partner is member of it.
                    // (e.g. to know when to display "invited" notification)
                    // Current partner can always be assumed to be a member of
                    // channels received at init.
                    convertedData.members = link(this.env.messaging.currentPartner);
                }
                const channel = this.env.models['mail.thread'].insert(
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
         * @param {Object[]} commandsData
         */
        _initCommands(commandsData) {
            this.messaging.update({
                commands: insert(commandsData),
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
            this.env.messaging.inbox.update({ counter: needaction_inbox_counter });
            this.env.messaging.starred.update({ counter: starred_counter });
        }

        /**
         * @private
         * @param {Object} mailFailuresData
         */
        async _initMailFailures(mailFailuresData) {
            await executeGracefully(mailFailuresData.map(messageData => () => {
                const message = this.env.models['mail.message'].insert(
                    this.env.models['mail.message'].convertData(messageData)
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
                    this.env.models['mail.partner'].convertData(current_partner),
                    {
                        user: insert({ id: currentUserId }),
                    }
                )),
                currentUser: insert({ id: currentUserId }),
                partnerRoot: insert(this.env.models['mail.partner'].convertData(partner_root)),
                publicPartners: insert(public_partners.map(
                    publicPartner => this.env.models['mail.partner'].convertData(publicPartner)
                ))
            });
        }

    }

    MessagingInitializer.fields = {
        messaging: one2one('mail.messaging', {
            inverse: 'initializer',
        }),
    };

    MessagingInitializer.modelName = 'mail.messaging_initializer';

    return MessagingInitializer;
}

registerNewModel('mail.messaging_initializer', factory);
