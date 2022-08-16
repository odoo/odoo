/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Country',
    recordMethods: {
        /**
         * @private
         * @returns {string|undefined}
         */
        _computeFlagUrl() {
            if (!this.code) {
                return clear();
            }
            return `/base/static/img/country_flags/${this.code}.png`;
        },
    },
    fields: {
        code: attr(),
        flagUrl: attr({
            compute: '_computeFlagUrl',
        }),
        id: attr({
            identifying: true,
            readonly: true,
            required: true,
        }),
        name: attr(),
    },
});
