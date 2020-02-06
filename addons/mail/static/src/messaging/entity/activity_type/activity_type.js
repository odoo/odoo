odoo.define('mail.messaging.entity.ActivityType', function (require) {
'use strict';

const { registerNewEntity } = require('mail.messaging.entity.core');

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

            this._write({
                displayName,
                id,
            });
        }

    }

    Object.assign(ActivityType, {
        relations: Object.assign({}, Entity.relations, {
            activities: {
                inverse: 'type',
                to: 'Activity',
                type: 'one2many',
            },
        }),
    });

    return ActivityType;
}

registerNewEntity('ActivityType', ActivityTypeFactory);

});
