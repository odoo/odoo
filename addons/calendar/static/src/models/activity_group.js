/** @odoo-module **/

import { addFields, addOnChanges, addRecordMethods, patchModelMethods } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';
// ensure that the model definition is loaded before the patch
import '@mail/models/activity_group';

patchModelMethods('ActivityGroup', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        data2.meetings = data.meetings;
        return data2;
    },
});

addRecordMethods('ActivityGroup', {
    /**
     * @private
     */
    _onChangeMeetings() {
        if (this.type === 'meeting' && this.meetings.length === 0) {
            this.delete();
        }
    },
});

addFields('ActivityGroup', {
    meetings: many('calendar.event'),
});

addOnChanges('ActivityGroup', [
    {
        dependencies: ['meetings', 'type'],
        methodName: '_onChangeMeetings',
    },
]);
