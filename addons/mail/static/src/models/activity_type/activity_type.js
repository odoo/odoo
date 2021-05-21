/** @odoo-module **/

import { attr, one2many } from '@mail/model/model_field';

export function factoryActivityType(dependencies) {

    class ActivityType extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

    }

    ActivityType.fields = {
        activities: one2many('mail.activity', {
            inverse: 'type',
        }),
        displayName: attr(),
        id: attr({
            required: true,
        }),
    };

    return ActivityType;
}
