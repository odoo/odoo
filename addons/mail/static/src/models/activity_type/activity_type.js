/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2many } from '@mail/model/model_field';

function factory(dependencies) {

    class ActivityType extends dependencies['mail.model'] {
    }

    ActivityType.fields = {
        activities: one2many('mail.activity', {
            inverse: 'type',
        }),
        displayName: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
    };
    ActivityType.identifyingFields = ['id'];
    ActivityType.modelName = 'mail.activity_type';

    return ActivityType;
}

registerNewModel('mail.activity_type', factory);
