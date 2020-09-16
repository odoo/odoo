odoo.define('mail/static/src/models/activity_type/activity_type.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2many } = require('mail/static/src/model/model_field_utils.js');

function factory(dependencies) {

    class ActivityType extends dependencies['mail.model'] {

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

    ActivityType.fields = {
        __mfield_activities: one2many('mail.activity', {
            inverse: '__mfield_type',
        }),
        __mfield_displayName: attr(),
        __mfield_id: attr(),
    };

    ActivityType.modelName = 'mail.activity_type';

    return ActivityType;
}

registerNewModel('mail.activity_type', factory);

});
