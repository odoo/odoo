odoo.define('mail/static/src/models/messaging/messaging.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2one } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class Messaging extends dependencies['mail.model'] {

        /**
         * @override
         */
        delete() {
            this.env.services['bus_service'].off('window_focus', null, this._handleGlobalWindowFocus);
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Open the form view of the record with provided id and model.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         */
        openDocument({ id, model }) {
            this.env.bus.trigger('do-action', {
                action: {
                    type: 'ir.actions.act_window',
                    res_model: model,
                    views: [[false, 'form']],
                    res_id: id,
                },
            });
            this.messagingMenu.close();
        }

        /**
         * Handles redirection to a model and id. Try to handle it in the context
         * of messaging (e.g. open chat if this is a user), otherwise fallback to
         * opening form view of record.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         * FIXME needs to be tested and maybe refactored (see task-2244279)
         */
        async redirect({ id, model }) {
            if (model === 'mail.channel') {
                const channel = this.env.models['mail.thread'].find(thread =>
                    thread.id === id &&
                    thread.model === 'mail.channel'
                );
                if (!channel || !channel.isPinned) {
                    this.env.models['mail.thread'].joinChannel(id, { autoselect: true });
                    return;
                }
                channel.open();
            } else if (model === 'res.partner') {
                if (id === this.currentPartner.id) {
                    this.openDocument({
                        model: 'res.partner',
                        id,
                    });
                    return;
                }
                const partner = this.env.models['mail.partner'].insert({ id });
                if (!partner.user) {
                    await this.async(() => partner.checkIsUser());
                }
                if (!partner.user) {
                    // partner is not a user, open document instead
                    this.openDocument({
                        model: 'res.partner',
                        id: partner.id,
                    });
                    return;
                }
                const chat = partner.correspondentThreads.find(thread =>
                    thread.channel_type === 'chat'
                );
                if (!chat) {
                    this.env.models['mail.thread'].createChannel({
                        autoselect: true,
                        partnerId: id,
                        type: 'chat',
                    });
                    return;
                }
                chat.open();
            } else {
                this.openDocument({
                    model: 'res.partner',
                    id,
                });
            }
        }

        /**
         * Start messaging and related records.
         */
        async start() {
            this._handleGlobalWindowFocus = this._handleGlobalWindowFocus.bind(this);
            this.env.services['bus_service'].on('window_focus', null, this._handleGlobalWindowFocus);
            await this.async(() => this.initializer.start());
            this.notificationHandler.start();
            this.update({ isInitialized: true });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _handleGlobalWindowFocus() {
            this.update({ outOfFocusUnreadMessageCounter: 0 });
            this.env.bus.trigger('set_title_part', {
                part: '_chat',
            });
        }

    }

    Messaging.fields = {
        cannedResponses: attr({
            default: {},
        }),
        chatWindowManager: one2one('mail.chat_window_manager', {
            autocreate: true,
            inverse: 'messaging',
            isCausal: true,
        }),
        commands: attr({
            default: {},
        }),
        currentPartner: one2one('mail.partner'),
        currentUser: one2one('mail.user'),
        device: one2one('mail.device', {
            autocreate: true,
            isCausal: true,
        }),
        dialogManager: one2one('mail.dialog_manager', {
            autocreate: true,
            isCausal: true,
        }),
        discuss: one2one('mail.discuss', {
            autocreate: true,
            inverse: 'messaging',
            isCausal: true,
        }),
        /**
         * Mailbox History.
         */
        history: one2one('mail.thread'),
        /**
         * Mailbox Inbox.
         */
        inbox: one2one('mail.thread'),
        initializer: one2one('mail.messaging_initializer', {
            autocreate: true,
            inverse: 'messaging',
            isCausal: true,
        }),
        isInitialized: attr({
            default: false,
        }),
        locale: one2one('mail.locale', {
            autocreate: true,
            isCausal: true,
        }),
        messagingMenu: one2one('mail.messaging_menu', {
            autocreate: true,
            inverse: 'messaging',
            isCausal: true,
        }),
        /**
         * Mailbox Moderation.
         */
        moderation: one2one('mail.thread'),
        notificationGroupManager: one2one('mail.notification_group_manager', {
            autocreate: true,
            isCausal: true,
        }),
        notificationHandler: one2one('mail.messaging_notification_handler', {
            autocreate: true,
            inverse: 'messaging',
            isCausal: true,
        }),
        outOfFocusUnreadMessageCounter: attr({
            default: 0,
        }),
        partnerRoot: many2one('mail.partner'),
        publicPartner: many2one('mail.partner'),
        /**
         * Mailbox Starred.
         */
        starred: one2one('mail.thread'),
    };

    Messaging.modelName = 'mail.messaging';

    return Messaging;
}

registerNewModel('mail.messaging', factory);

});
