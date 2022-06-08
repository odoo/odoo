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
        _computeInputPlaceholder() {
            return this.env._t("Ask something ...");
        },
    },
    fields: {
        inputPlaceholder: attr({
            compute: '_computeInputPlaceholder',
        }),
    },
});
