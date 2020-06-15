odoo.define('mail/static/src/models/notification_group/notification_group.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class NotificationGroup extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Opens the view that allows to cancel all notifications of the group.
         */
        openCancelAction() {
            const device = this.env.messaging.device;
            if (this.notification_type === 'email') {
                this.env.bus.trigger('do-action', {
                    action: 'mail.mail_resend_cancel_action',
                    options: {
                        additional_context: {
                            default_model: this.res_model,
                            unread_counter: this.notifications.length,
                        },
                    },
                });
            }
            if (!device.isMobile) {
                this.env.messaging.messagingMenu.close();
            }
        }

        /**
         * Opens the view that displays either the single record of the group or
         * all the records in the group.
         */
        openDocuments() {
            if (this.res_id) {
                if (this.res_model === 'mail.channel') {
                    const channel = this.env.models['mail.thread'].insert({
                        id: this.res_id,
                        model: this.res_model,
                    });
                    channel.open();
                } else {
                    this.env.messaging.openDocument({
                        id: this.res_id,
                        model: this.res_model,
                    });
                }
            } else {
                this._openDocuments();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _createRecordLocalId(data) {
            const NotificationGroup = this.env.models['mail.notification_group'];
            return `${NotificationGroup.modelName}_${data.id}`;
        }

        /**
         * Opens the view that displays all the records of the group.
         *
         * @private
         */
        _openDocuments() {
            const device = this.env.messaging.device;
            if (this.notification_type === 'email') {
                this.env.bus.trigger('do-action', {
                    action: {
                        name: this.env._t("Mail Failures"),
                        type: 'ir.actions.act_window',
                        view_mode: 'kanban,list,form',
                        views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                        target: 'current',
                        res_model: this.res_model,
                        domain: [['message_has_error', '=', true]],
                    },
                });
            }
            if (!device.isMobile) {
                this.env.messaging.messagingMenu.close();
            }
        }

    }

    NotificationGroup.fields = {
        date: attr(),
        id: attr(),
        notification_type: attr(),
        notifications: one2many('mail.notification'),
        res_id: attr(),
        res_model: attr(),
        res_model_name: attr(),
    };

    NotificationGroup.modelName = 'mail.notification_group';

    return NotificationGroup;
}

registerNewModel('mail.notification_group', factory);

});
