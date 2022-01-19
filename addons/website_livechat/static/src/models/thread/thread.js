/** @odoo-module **/

import { addFields, patchModelMethods } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insert, unlink } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread/thread';

patchModelMethods('Thread', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('visitor' in data) {
            if (data.visitor) {
                data2.visitor = insert(this.messaging.models['Visitor'].convertData(data.visitor));
            } else {
                data2.visitor = unlink();
            }
        }
        return data2;
    },
});

addFields('Thread', {
    /**
     * Visitor connected to the livechat.
     */
    visitor: one('Visitor', {
        inverse: 'threads',
    }),
});
