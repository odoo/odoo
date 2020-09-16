odoo.define('mail/static/src/models/messaging/messaging.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many, one2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class Messaging extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willDelete() {
            this.env.services['bus_service'].off('window_focus', null, this._handleGlobalWindowFocus);
            return super._willDelete(...arguments);
        }

        /**
         * Starts messaging and related records.
         */
        async start() {
            this._handleGlobalWindowFocus = this._handleGlobalWindowFocus.bind(this);
            this.env.services['bus_service'].on('window_focus', null, this._handleGlobalWindowFocus);
            await this.async(() => this.__mfield_initializer(this).start());
            this.__mfield_notificationHandler(this).start();
            this.update({
                __mfield_isInitialized: true,
            });
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Gets the chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} param0
         * @param {integer} [param0.partnerId]
         * @param {integer} [param0.userId]
         * @param {Object} [options]
         * @returns {mail.thread|undefined}
         */
        async getChat({ partnerId, userId }) {
            if (userId) {
                const user = this.env.models['mail.user'].insert({
                    __mfield_id: userId,
                });
                return user.getChat();
            }
            if (partnerId) {
                const partner = this.env.models['mail.partner'].insert({
                    __mfield_id: partnerId,
                });
                return partner.getChat();
            }
        }

        /**
         * Opens a chat with the provided person and returns it.
         *
         * If a chat is not appropriate, a notification is displayed instead.
         *
         * @param {Object} person forwarded to @see `getChat()`
         * @param {Object} [options] forwarded to @see `mail.thread:open()`
         * @returns {mail.thread|undefined}
         */
        async openChat(person, options) {
            const chat = await this.async(() => this.getChat(person));
            if (!chat) {
                return;
            }
            await this.async(() => chat.open(options));
            return chat;
        }

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
            if (this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.env.messaging.__mfield_messagingMenu(this).close();
            }
        }

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
                const partner = this.env.models['mail.partner'].insert({
                    __mfield_id: id,
                });
                return partner.openProfile();
            }
            if (model === 'res.users') {
                const user = this.env.models['mail.user'].insert({
                    __mfield_id: id,
                });
                return user.openProfile();
            }
            if (model === 'mail.channel') {
                let channel = this.env.models['mail.thread'].findFromIdentifyingData({
                    __mfield_: id,
                    __mfield_model: 'mail.channel',
                });
                if (!channel) {
                    channel = (await this.async(() =>
                        this.env.models['mail.thread'].performRpcChannelInfo({ ids: [id] })
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
            return this.env.messaging.openDocument({ id, model });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _handleGlobalWindowFocus() {
            this.update({
                __mfield_outOfFocusUnreadMessageCounter: 0,
            });
            this.env.bus.trigger('set_title_part', {
                part: '_chat',
            });
        }

    }

    Messaging.fields = {
        __mfield_cannedResponses: one2many('mail.canned_response'),
        __mfield_chatWindowManager: one2one('mail.chat_window_manager', {
            default: [['create']],
            inverse: '__mfield_messaging',
            isCausal: true,
        }),
        __mfield_commands: one2many('mail.channel_command'),
        __mfield_currentPartner: one2one('mail.partner'),
        __mfield_currentUser: one2one('mail.user'),
        __mfield_device: one2one('mail.device', {
            default: [['create']],
            isCausal: true,
        }),
        __mfield_dialogManager: one2one('mail.dialog_manager', {
            default: [['create']],
            isCausal: true,
        }),
        __mfield_discuss: one2one('mail.discuss', {
            default: [['create']],
            inverse: '__mfield_messaging',
            isCausal: true,
        }),
        /**
         * Mailbox History.
         */
        __mfield_history: one2one('mail.thread'),
        /**
         * Mailbox Inbox.
         */
        __mfield_inbox: one2one('mail.thread'),
        __mfield_initializer: one2one('mail.messaging_initializer', {
            default: [['create']],
            inverse: '__mfield_messaging',
            isCausal: true,
        }),
        __mfield_isInitialized: attr({
            default: false,
        }),
        __mfield_locale: one2one('mail.locale', {
            default: [['create']],
            isCausal: true,
        }),
        __mfield_messagingMenu: one2one('mail.messaging_menu', {
            default: [['create']],
            inverse: '__mfield_messaging',
            isCausal: true,
        }),
        /**
         * Mailbox Moderation.
         */
        __mfield_moderation: one2one('mail.thread'),
        __mfield_notificationGroupManager: one2one('mail.notification_group_manager', {
            default: [['create']],
            isCausal: true,
        }),
        __mfield_notificationHandler: one2one('mail.messaging_notification_handler', {
            default: [['create']],
            inverse: '__mfield_messaging',
            isCausal: true,
        }),
        __mfield_outOfFocusUnreadMessageCounter: attr({
            default: 0,
        }),
        __mfield_partnerRoot: many2one('mail.partner'),
        __mfield_publicPartner: many2one('mail.partner'),
        /**
         * Mailbox Starred.
         */
        __mfield_starred: one2one('mail.thread'),
    };

    Messaging.modelName = 'mail.messaging';

    return Messaging;
}

registerNewModel('mail.messaging', factory);

});
