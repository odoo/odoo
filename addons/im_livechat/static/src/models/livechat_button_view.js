/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'LivechatButtonView',
    identifyingFields: ['messaging'],
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeDefaultUsername() {
            return this.env._t("Visitor");
        },
    },
    fields: {
        defaultUsername: attr({
            compute: '_computeDefaultUsername',
        }),
    },
});
