odoo.define('mail/static/src/models/activity_type/activity_type.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, one2many } = require('mail/static/src/model/model_field.js');

function factory(dependencies) {

    class ActivityType extends dependencies['mail.model'] {}

    ActivityType.fields = {
        activities: one2many('mail.activity', {
            inverse: 'type',
        }),
        displayName: attr(),
        id: attr(),
    };

    ActivityType.modelName = 'mail.activity_type';

    return ActivityType;
}

registerNewModel('mail.activity_type', factory);

});
