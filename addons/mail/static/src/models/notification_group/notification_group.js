odoo.define('mail/static/src/models/notification_group/notification_group.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class NotificationGroup extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Opens the view that allows to cancel all notifications of the group.
         */
        openCancelAction() {
            if (this.notification_type !== 'email') {
                return;
            }
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

        /**
         * Opens the view that displays either the single record of the group or
         * all the records in the group.
         */
        openDocuments() {
            if (this.thread) {
                this.thread.open();
            } else {
                this._openDocuments();
            }
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @returns {mail.thread|undefined}
         */
        _computeThread() {
            if (this.res_id) {
                return [['insert', {
                    id: this.res_id,
                    model: this.res_model,
                }]];
            }
            return [['unlink']];
        }

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * Opens the view that displays all the records of the group.
         *
         * @private
         */
        _openDocuments() {
            if (this.notification_type !== 'email') {
                return;
            }
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
            if (this.env.messaging.device.isMobile) {
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
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
        /**
         * Related thread when the notification group concerns a single thread.
         */
        thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                'res_id',
                'res_model',
            ],
        })
    };

    NotificationGroup.modelName = 'mail.notification_group';

    return NotificationGroup;
}

registerNewModel('mail.notification_group', factory);

});
