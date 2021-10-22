/** @odoo-module **/

import { addFields, patchModelMethods } from '@mail/model/model_core';
import { many2one } from '@mail/model/model_field';
import { insert, unlink } from '@mail/model/model_field_command';
// ensure that the model definition is loaded before the patch
import '@mail/models/thread/thread';

patchModelMethods('mail.thread', {
    /**
     * @override
     */
    convertData(data) {
        const data2 = this._super(data);
        if ('visitor' in data) {
            if (data.visitor) {
                data2.visitor = insert(this.messaging.models['website_livechat.visitor'].convertData(data.visitor));
            } else {
                data2.visitor = unlink();
            }
        }
        return data2;
    },
});

addFields('mail.thread', {
    /**
     * Visitor connected to the livechat.
     */
    visitor: many2one('website_livechat.visitor', {
        inverse: 'threads',
    }),
});
