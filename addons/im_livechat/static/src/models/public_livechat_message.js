/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'PublicLivechatMessage',
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand|integer}
         */
        _computeAuthorId() {
            if (!(this.data.author_id && this.data.author_id[0])) {
                return clear();
            }
            return this.data.author_id[0];
        },
    },
    fields: {
        authorId: attr({
            compute: '_computeAuthorId',
        }),
        data: attr(),
        id: attr({
            identifying: true,
        }),
        widget: attr(),
    },
});
