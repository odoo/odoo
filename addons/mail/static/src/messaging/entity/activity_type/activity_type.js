odoo.define('mail.messaging.entity.ActivityType', function (require) {
'use strict';

const {
    fields: {
        one2many,
    },
    registerNewEntity,
} = require('mail.messaging.entity.core');

function ActivityTypeFactory({ Entity }) {

    class ActivityType extends Entity {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        _update(data) {
            let {
                displayName = this.displayName,
                id = this.id,
            } = data;

            Object.assign(this, {
                displayName,
                id,
            });
        }

    }

    Object.assign(ActivityType, {
        fields: Object.assign({}, Entity.fields, {
            activities: one2many('Activity', {
                inverse: 'type',
            }),
        }),
    });

    return ActivityType;
}

registerNewEntity('ActivityType', ActivityTypeFactory);

});
