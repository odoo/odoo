odoo.define('mail/static/src/models/messaging_initializer/messaging_initializer.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { one2one } = require('mail/static/src/model/model_field_utils.js');

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
            this.__mfield_messaging(this).update({
                __mfield_history: [['create', {
                    __mfield_id: 'history',
                    __mfield_isServerPinned: true,
                    __mfield_model: 'mail.box',
                    __mfield_name: this.env._t("History"),
                }]],
                __mfield_inbox: [['create', {
                    __mfield_id: 'inbox',
                    __mfield_isServerPinned: true,
                    __mfield_model: 'mail.box',
                    __mfield_name: this.env._t("Inbox"),
                }]],
                __mfield_moderation: [['create', {
                    __mfield_id: 'moderation',
                    __mfield_model: 'mail.box',
                    __mfield_name: this.env._t("Moderation"),
                }]],
                __mfield_starred: [['create', {
                    __mfield_id: 'starred',
                    __mfield_isServerPinned: true,
                    __mfield_model: 'mail.box',
                    __mfield_name: this.env._t("Starred"),
                }]],
            });
            const device = this.__mfield_messaging(this).__mfield_device(this);
            device.start();
            const context = Object.assign({
                isMobile: device.__mfield_isMobile(this),
            }, this.env.session.user_context);
            const discuss = this.__mfield_messaging(this).__mfield_discuss(this);
            const data = await this.async(() => this.env.services.rpc({
                route: '/mail/init_messaging',
                params: { context: context }
            }));
            await this.async(() => this._init(data));
            if (discuss.__mfield_isOpen(this)) {
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
         * @param {Object[]} [param0.mention_partner_suggestions=[]]
         * @param {Object[]} [param0.moderation_channel_ids=[]]
         * @param {integer} [param0.moderation_counter=0]
         * @param {integer} [param0.needaction_inbox_counter=0]
         * @param {Object} param0.partner_root
         * @param {Object} param0.public_partner
         * @param {Object[]} [param0.shortcodes=[]]
         * @param {integer} [param0.starred_counter=0]
         */
        async _init({
            channel_slots,
            commands = [],
            current_partner,
            current_user_id,
            mail_failures = {},
            mention_partner_suggestions = [],
            menu_id,
            moderation_channel_ids = [],
            moderation_counter = 0,
            needaction_inbox_counter = 0,
            partner_root,
            public_partner,
            shortcodes = [],
            starred_counter = 0
        }) {
            const discuss = this.__mfield_messaging(this).__mfield_discuss(this);
            // partners first because the rest of the code relies on them
            this._initPartners({
                current_partner,
                current_user_id,
                moderation_channel_ids,
                partner_root,
                public_partner,
            });
            // mailboxes after partners and before other initializers that might
            // manipulate threads or messages
            this._initMailboxes({
                moderation_channel_ids,
                moderation_counter,
                needaction_inbox_counter,
                starred_counter,
            });
            // various suggestions in no particular order
            this._initCannedResponses(shortcodes);
            this._initCommands(commands);
            await this.async(() => this._initMentionPartnerSuggestions(mention_partner_suggestions));
            // channels when the rest of messaging is ready
            await this.async(() => this._initChannels(channel_slots));
            // failures after channels
            this._initMailFailures(mail_failures);
            discuss.update({
                __mfield_menu_id: menu_id,
            });
        }

        /**
         * @private
         * @param {Object[]} cannedResponsesData
         */
        _initCannedResponses(cannedResponsesData) {
            this.__mfield_messaging(this).update({
                __mfield_cannedResponses: [['insert', cannedResponsesData.map(data => {
                    return {
                        __mfield_id: data.id,
                        __mfield_source: data.source,
                        __mfield_substitution: data.substitution,
                    };
                })]],
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
            for (const channelData of channelsData) {
                // there might be a lot of channels, insert each of them one by
                // one asynchronously to avoid blocking the UI
                await this.async(() => new Promise(resolve => setTimeout(resolve)));
                this.env.models['mail.thread'].insert(
                    this.env.models['mail.thread'].convertData(channelData)
                );
            }
        }

        /**
         * @private
         * @param {Object[]} commandsData
         */
        _initCommands(commandsData) {
            this.__mfield_messaging(this).update({
                __mfield_commands: [['insert', commandsData.map(data => {
                    return {
                        __mfield_channel_types: data.channel_types,
                        __mfield_help: data.help,
                        __mfield_name: data.name,
                    };
                })]],
            });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {Object[]} [param0.moderation_channel_ids=[]]
         * @param {integer} param0.moderation_counter
         * @param {integer} param0.needaction_inbox_counter
         * @param {integer} param0.starred_counter
         */
        _initMailboxes({
            moderation_channel_ids,
            moderation_counter,
            needaction_inbox_counter,
            starred_counter,
        }) {
            this.env.messaging.__mfield_inbox(this).update({
                __mfield_counter: needaction_inbox_counter,
            });
            this.env.messaging.__mfield_starred(this).update({
                __mfield_counter: starred_counter,
            });
            if (moderation_channel_ids.length > 0) {
                this.__mfield_messaging(this).__mfield_moderation(this).update({
                    __mfield_counter: moderation_counter,
                    __mfield_isServerPinned: true,
                });
            }
        }

        /**
         * @private
         * @param {Object} mailFailuresData
         */
        _initMailFailures(mailFailuresData) {
            const messages = this.env.models['mail.message'].insert(mailFailuresData.map(
                messageData => this.env.models['mail.message'].convertData(messageData)
            ));
            for (const message of messages) {
                // implicit: failures are sent by the server at initialization
                // only if the current partner is author of the message
                if (!message.__mfield_author(this) && this.__mfield_messaging(this).__mfield_currentPartner(this)) {
                    message.update({
                        __mfield_author: [['link', this.__mfield_messaging(this).__mfield_currentPartner(this)]],
                    });
                }
            }
            this.__mfield_messaging(this).__mfield_notificationGroupManager(this).computeGroups();
            // manually force recompute of counter (after computing the groups)
            this.__mfield_messaging(this).__mfield_messagingMenu(this).update();
        }

        /**
         * @private
         * @param {Object[]} mentionPartnerSuggestionsData
         */
        async _initMentionPartnerSuggestions(mentionPartnerSuggestionsData) {
            for (const suggestions of mentionPartnerSuggestionsData) {
                for (const suggestion of suggestions) {
                    // there might be a lot of partners, insert each of them one
                    // by one asynchronously to avoid blocking the UI
                    await this.async(() => new Promise(resolve => setTimeout(resolve)));
                    const { email, id, name } = suggestion;
                    this.env.models['mail.partner'].insert({
                        __mfield_email: email,
                        __mfield_id: id,
                        __mfield_name: name,
                    });
                }
            }
        }

        /**
         * @private
         * @param {Object} current_partner
         * @param {boolean} current_partner.active
         * @param {string} current_partner.display_name
         * @param {integer} current_partner.id
         * @param {string} current_partner.name
         * @param {integer} current_user_id
         * @param {integer[]} moderation_channel_ids
         * @param {Object} partner_root
         * @param {boolean} partner_root.active
         * @param {string} partner_root.display_name
         * @param {integer} partner_root.id
         * @param {string} partner_root.name
         * @param {Object} public_partner
         * @param {boolean} public_partner.active
         * @param {string} public_partner.display_name
         * @param {integer} public_partner.id
         * @param {string} public_partner.name
         */
        _initPartners({
            current_partner: {
                active: currentPartnerIsActive,
                display_name: currentPartnerDisplayName,
                id: currentPartnerId,
                name: currentPartnerName,
            },
            current_user_id: currentUserId,
            moderation_channel_ids = [],
            partner_root: {
                active: partnerRootIsActive,
                display_name: partnerRootDisplayName,
                id: partnerRootId,
                name: partnerRootName,
            },
            public_partner: {
                active: publicPartnerIsActive,
                display_name: publicPartnerDisplayName,
                id: publicPartnerId,
                name: publicPartnerName,
            },
        }) {
            this.__mfield_messaging(this).update({
                __mfield_currentPartner: [['insert', {
                    __mfield_active: currentPartnerIsActive,
                    __mfield_display_name: currentPartnerDisplayName,
                    __mfield_id: currentPartnerId,
                    __mfield_moderatedChannels: [
                        ['insert', moderation_channel_ids.map(id => {
                            return {
                                __mfield_id: id,
                                __mfield_model: 'mail.channel',
                            };
                        })],
                    ],
                    __mfield_name: currentPartnerName,
                    __mfield_user: [['insert', {
                        __mfield_id: currentUserId,
                    }]],
                }]],
                __mfield_currentUser: [['insert', {
                    __mfield_id: currentUserId,
                }]],
                __mfield_partnerRoot: [['insert', {
                    __mfield_active: partnerRootIsActive,
                    __mfield_display_name: partnerRootDisplayName,
                    __mfield_id: partnerRootId,
                    __mfield_name: partnerRootName,
                }]],
                __mfield_publicPartner: [['insert', {
                    __mfield_active: publicPartnerIsActive,
                    __mfield_display_name: publicPartnerDisplayName,
                    __mfield_id: publicPartnerId,
                    __mfield_name: publicPartnerName,
                }]],
            });
        }

    }

    MessagingInitializer.fields = {
        __mfield_messaging: one2one('mail.messaging', {
            inverse: '__mfield_initializer',
        }),
    };

    MessagingInitializer.modelName = 'mail.messaging_initializer';

    return MessagingInitializer;
}

registerNewModel('mail.messaging_initializer', factory);

});
