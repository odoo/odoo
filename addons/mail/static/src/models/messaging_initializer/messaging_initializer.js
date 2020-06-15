odoo.define('mail/static/src/models/messaging_initializer/messaging_initializer.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { one2one } = require('mail/static/src/model/model_field.js');

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
            await this.async(() => this.env.session.is_bound);

            this.messaging.update({
                history: [['create', {
                    id: 'history',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("History"),
                }]],
                inbox: [['create', {
                    id: 'inbox',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("Inbox"),
                }]],
                starred: [['create', {
                    id: 'starred',
                    isServerPinned: true,
                    model: 'mail.box',
                    name: this.env._t("Starred"),
                }]],
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
            }));
            this._init(data);
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
         * @param {boolean} [param0.is_moderator=false]
         * @param {Object} [param0.mail_failures={}]
         * @param {Object[]} [param0.mention_partner_suggestions=[]]
         * @param {Object[]} [param0.moderation_channel_ids=[]]
         * @param {integer} [param0.moderation_counter=0]
         * @param {integer} [param0.needaction_inbox_counter=0]
         * @param {Array} param0.partner_root
         * @param {Object[]} [param0.shortcodes=[]]
         * @param {integer} [param0.starred_counter=0]
         */
        _init({
            channel_slots,
            commands = [],
            is_moderator = false,
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
            const discuss = this.messaging.discuss;
            this._initPartners({
                moderation_channel_ids,
                partner_root,
                public_partner,
            });
            this._initChannels(channel_slots);
            this._initCommands(commands);
            this._initMailboxes({
                is_moderator,
                moderation_counter,
                needaction_inbox_counter,
                starred_counter,
            });
            this._initMailFailures(mail_failures);
            this._initCannedResponses(shortcodes);
            this._initMentionPartnerSuggestions(mention_partner_suggestions);
            discuss.update({ menu_id });
        }

        /**
         * @private
         * @param {Object[]} shortcodes
         */
        _initCannedResponses(shortcodes) {
            const messaging = this.messaging;
            const cannedResponses = shortcodes
                .map(s => {
                    const { id, source, substitution } = s;
                    return { id, source, substitution };
                })
                .reduce((obj, cr) => {
                    obj[cr.id] = cr;
                    return obj;
                }, {});
            messaging.update({ cannedResponses });
        }

        /**
         * @private
         * @param {Object} [param0={}]
         * @param {Object[]} [param0.channel_channel=[]]
         * @param {Object[]} [param0.channel_direct_message=[]]
         * @param {Object[]} [param0.channel_private_group=[]]
         */
        _initChannels({
            channel_channel = [],
            channel_direct_message = [],
            channel_private_group = [],
        } = {}) {
            for (const data of channel_channel.concat(channel_direct_message, channel_private_group)) {
                this.env.models['mail.thread'].insert(
                    this.env.models['mail.thread'].convertData(data),
                );
            }
        }

        /**
         * @private
         * @param {Object[]} commandsData
         */
        _initCommands(commandsData) {
            const messaging = this.messaging;
            const commands = commandsData
                .map(command => {
                    return Object.assign({
                        id: command.name,
                    }, command);
                })
                .reduce((obj, command) => {
                    obj[command.id] = command;
                    return obj;
                }, {});
            messaging.update({ commands });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {boolean} param0.is_moderator
         * @param {integer} param0.moderation_counter
         * @param {integer} param0.needaction_inbox_counter
         * @param {integer} param0.starred_counter
         */
        _initMailboxes({
            is_moderator,
            moderation_counter,
            needaction_inbox_counter,
            starred_counter,
        }) {
            this.env.messaging.inbox.update({ counter: needaction_inbox_counter });
            this.env.messaging.starred.update({ counter: starred_counter });
            if (is_moderator) {
                this.messaging.update({
                    moderation: [['create', {
                        counter: moderation_counter,
                        id: 'moderation',
                        isServerPinned: true,
                        model: 'mail.box',
                        name: this.env._t("Moderation"),
                    }]],
                });
            }
        }

        /**
         * @private
         * @param {Object} mailFailuresData
         */
        _initMailFailures(mailFailuresData) {
            for (const messageData of mailFailuresData) {
                const message = this.env.models['mail.message'].insert(
                    this.env.models['mail.message'].convertData(messageData)
                );
                // implicit: failures are sent by the server at initialization
                // only if the current partner is author of the message
                if (!message.author && this.messaging.currentPartner) {
                    message.update({ author: [['link', this.messaging.currentPartner]] });
                }
            }
            this.messaging.notificationGroupManager.computeGroups();
            // manually force recompute of counter (after computing the groups)
            this.messaging.messagingMenu.update();
        }

        /**
         * @private
         * @param {Object[]} mentionPartnerSuggestionsData
         */
        _initMentionPartnerSuggestions(mentionPartnerSuggestionsData) {
            for (const suggestions of mentionPartnerSuggestionsData) {
                for (const suggestion of suggestions) {
                    const { email, id, name } = suggestion;
                    this.env.models['mail.partner'].insert({ email, id, name });
                }
            }
        }

        /**
         * @private
         * @param {Array} param0 partner root name get
         * @param {integer} param0[0] partner root id
         * @param {string} param0[1] partner root display_name
         */
        _initPartners({
            moderation_channel_ids = [],
            partner_root: {
                active: partnerRootIsActive,
                display_name: partnerRootDisplayName,
                id: partnerRootId,
            },
            public_partner: {
                active: publicPartnerIsActive,
                display_name: publicPartnerDisplayName,
                id: publicPartnerId,
            },
        }) {
            this.messaging.update({
                currentPartner: [['insert', {
                    display_name: this.env.session.partner_display_name,
                    id: this.env.session.partner_id,
                    moderatedChannelIds: moderation_channel_ids,
                    name: this.env.session.name,
                    user: [['insert', { id: this.env.session.uid }]],
                }]],
                currentUser: [['insert', { id: this.env.session.uid }]],
                partnerRoot: [['insert', {
                    active: partnerRootIsActive,
                    display_name: partnerRootDisplayName,
                    id: partnerRootId,
                }]],
                publicPartner: [['insert', {
                    active: publicPartnerIsActive,
                    display_name: publicPartnerDisplayName,
                    id: publicPartnerId,
                }]],
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

});
