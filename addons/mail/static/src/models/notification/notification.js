odoo.define('mail/static/src/models/notification/notification.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2one } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class Notification extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
        static convertData(data) {
            const data2 = {};
            if ('failure_type' in data) {
                data2.__mfield_failure_type = data.failure_type;
            }
            if ('id' in data) {
                data2.__mfield_id = data.id;
            }
            if ('notification_status' in data) {
                data2.__mfield_notification_status = data.notification_status;
            }
            if ('notification_type' in data) {
                data2.__mfield_notification_type = data.notification_type;
            }
            if ('res_partner_id' in data) {
                if (!data.res_partner_id) {
                    data2.__mfield_partner = [['unlink-all']];
                } else {
                    data2.__mfield_partner = [
                        ['insert', {
                            __mfield_display_name: data.res_partner_id[1],
                            __mfield_id: data.res_partner_id[0],
                        }],
                    ];
                }
            }
            return data2;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.__mfield_id}`;
        }

    }

    Notification.fields = {
        __mfield_failure_type: attr(),
        __mfield_id: attr(),
        __mfield_message: many2one('mail.message', {
            inverse: '__mfield_notifications',
        }),
        __mfield_notification_status: attr(),
        __mfield_notification_type: attr(),
        __mfield_partner: many2one('mail.partner'),
    };

    Notification.modelName = 'mail.notification';

    return Notification;
}

registerNewModel('mail.notification', factory);

});
