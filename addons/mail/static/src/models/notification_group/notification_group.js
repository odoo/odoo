odoo.define('mail/static/src/models/notification_group/notification_group.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one, one2many } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class NotificationGroup extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Opens the view that allows to cancel all notifications of the group.
         */
        openCancelAction() {
            if (this.__mfield_notification_type(this) !== 'email') {
                return;
            }
            this.env.bus.trigger('do-action', {
                action: 'mail.mail_resend_cancel_action',
                options: {
                    additional_context: {
                        default_model: this.__mfield_res_model(this),
                        unread_counter: this.__mfield_notifications(this).length,
                    },
                },
            });
        }

        /**
         * Opens the view that displays either the single record of the group or
         * all the records in the group.
         */
        openDocuments() {
            if (this.__mfield_thread(this)) {
                this.__mfield_thread(this).open();
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
            if (this.__mfield_res_id(this)) {
                return [['insert', {
                    __mfield_id: this.__mfield_res_id(this),
                    __mfield_model: this.__mfield_res_model(this),
                }]];
            }
            return [['unlink']];
        }

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

        /**
         * Opens the view that displays all the records of the group.
         *
         * @private
         */
        _openDocuments() {
            if (this.__mfield_notification_type(this) !== 'email') {
                return;
            }
            this.env.bus.trigger('do-action', {
                action: {
                    name: this.env._t("Mail Failures"),
                    type: 'ir.actions.act_window',
                    view_mode: 'kanban,list,form',
                    views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
                    target: 'current',
                    res_model: this.__mfield_res_model(this),
                    domain: [['message_has_error', '=', true]],
                },
            });
            if (this.env.messaging.__mfield_device(this).__mfield_isMobile(this)) {
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.env.messaging.__mfield_messagingMenu(this).close();
            }
        }

    }

    NotificationGroup.fields = {
        __mfield_date: attr(),
        __mfield_id: attr(),
        __mfield_notification_type: attr(),
        __mfield_notifications: one2many('mail.notification'),
        __mfield_res_id: attr(),
        __mfield_res_model: attr(),
        __mfield_res_model_name: attr(),
        /**
         * Related thread when the notification group concerns a single thread.
         */
        __mfield_thread: many2one('mail.thread', {
            compute: '_computeThread',
            dependencies: [
                '__mfield_res_id',
                '__mfield_res_model',
            ],
        })
    };

    NotificationGroup.modelName = 'mail.notification_group';

    return NotificationGroup;
}

registerNewModel('mail.notification_group', factory);

});
