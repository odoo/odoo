/** @odoo-module **/

import { registerPatch } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';

registerPatch({
    name: 'ActivityGroup',
    modelMethods: {
        /**
         * @override
         */
        convertData(data) {
            const data2 = this._super(data);
            data2.meetings = data.meetings;
            return data2;
        },
    },
    recordMethods: {
        _onChangeMeetings() {
            if (this.type === 'meeting' && this.meetings.length === 0) {
                this.delete();
            }
        },
    },
    fields: {
        meetings: many('calendar.event'),
    },
    onChanges: [
        {
            dependencies: ['meetings', 'type'],
            methodName: '_onChangeMeetings',
        },
    ],
});
