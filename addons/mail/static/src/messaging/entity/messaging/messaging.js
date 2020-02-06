odoo.define('mail.messaging.entity.Messaging', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

function MessagingFactory({ Entity }) {

    class Messaging extends Entity {

        /**
         * @override
         */
        static create(...args) {
            const messaging = super.create(...args);

            const initializer = this.env.entities.MessagingInitializer.create();
            messaging.link({ initializer });

            const notificationHandler = this.env.entities.MessagingNotificationHandler.create();
            messaging.link({ notificationHandler });

            return messaging;
        }
        /**
         * @override
         */
        static delete() {
            this.env.call('bus_service', 'off', 'window_focus', null, this._handleGlobalWindowFocus);
            super.delete();
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        async start() {
            this._handleGlobalWindowFocus = this._handleGlobalWindowFocus.bind(this);
            this.env.call('bus_service', 'on', 'window_focus', null, this._handleGlobalWindowFocus);
            await this.initializer.start();
            this.notificationHandler.start();
            this.update({ isInitialized: true });
        }

        /**
         * Handles redirection to a model and id. Try to handle it in the context
         * of messaging (e.g. open chat if this is a user), otherwise fallback to
         * opening form view of record.
         *
         * @param {Object} param0
         * @param {integer} param0.id
         * @param {string} param0.model
         */
        async redirect({ id, model }) {
            if (model === 'mail.channel') {
                const channel = this.env.entities.Thread.channelFromId(id);
                if (!channel) {
                    this.env.entities.Thread.joinChannel(id, { autoselect: true });
                    return;
                }
                channel.open();
            } else if (model === 'res.partner') {
                if (id === this.currentPartner) {
                    this._openDocument({
                        model: 'res.partner',
                        id,
                    });
                    return;
                }
                const partner = this.env.entities.Partner.insert({ id });
                if (partner.userId === undefined) {
                    await partner.checkIsUser();
                }
                if (partner.userId === null) {
                    // partner is not a user, open document instead
                    this._openDocument({
                        model: 'res.partner',
                        id: partner.id,
                    });
                    return;
                }
                const chat = partner.directPartnerThread;
                if (!chat) {
                    this.env.entities.Thread.createChannel({
                        autoselect: true,
                        partnerId: id,
                        type: 'chat',
                    });
                    return;
                }
                chat.open();
            } else {
                this._openDocument({
                    model: 'res.partner',
                    id,
                });
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update(data) {
            const {
                cannedReponses = this.cannedReponses || {},
                commands = this.commands || {},
                isInitialized = this.isInitialized || false,
                outOfFocusUnreadMessageCounter = this.outOfFocusUnreadMessageCounter || 0,
            } = data;
            this._write({
                cannedReponses,
                commands,
                isInitialized,
                outOfFocusUnreadMessageCounter,
            });
        }

        /**
         * @private
         * @param {Object} param0
         * @param {Object} param0.env
         * @param {Object} param0.state
         */
        _handleGlobalWindowFocus() {
            this.update({ outOfFocusUnreadMessageCounter: 0 });
            this.env.trigger_up('set_title_part', {
                part: '_chat',
            });
        }

        /**
         * Open the form view of the record with provided id and model.
         *
         * @private
         * @param {integer} param1.id
         * @param {string} param1.model
         */
        _openDocument({ id, model }) {
            this.env.do_action({
                type: 'ir.actions.act_window',
                res_model: model,
                views: [[false, 'form']],
                res_id: id,
            });
            this.messagingMenu.close();
            this.env.entities.ChatWindow.closeAll();
        }

    }

    Object.assign(Messaging, {
        relations: Object.assign({}, Entity.relations, {
            attachmentViewer: {
                inverse: 'messaging',
                isCausal: true,
                to: 'AttachmentViewer',
                type: 'one2one',
            },
            currentPartner: {
                inverse: 'currentPartnerMessaging',
                to: 'Partner',
                type: 'one2one',
            },
            device: {
                inverse: 'messaging',
                isCausal: true,
                to: 'Device',
                type: 'one2one',
            },
            discuss: {
                inverse: 'messaging',
                isCausal: true,
                to: 'Discuss',
                type: 'one2one',
            },
            initializer: {
                inverse: 'messaging',
                isCausal: true,
                to: 'MessagingInitializer',
                type: 'one2one',
            },
            locale: {
                inverse: 'messaging',
                isCausal: true,
                to: 'Locale',
                type: 'one2one',
            },
            messagingMenu: {
                inverse: 'messaging',
                isCausal: true,
                to: 'MessagingMenu',
                type: 'one2one',
            },
            notificationHandler: {
                inverse: 'messaging',
                isCausal: true,
                to: 'MessagingNotificationHandler',
                type: 'one2one',
            },
            partnerRoot: {
                inverse: 'partnerRootMessaging',
                to: 'Partner',
                type: 'one2one',
            },
        }),
    });

    return Messaging;
}

registerNewEntity('Messaging', MessagingFactory);

});
