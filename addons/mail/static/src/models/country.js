/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'Country',
    fields: {
        code: attr(),
        flagUrl: attr({
            compute() {
                if (!this.code) {
                    return clear();
                }
                return `/base/static/img/country_flags/${this.code}.png`;
            },
        }),
        id: attr({
            identifying: true,
        }),
        name: attr(),
    },
});
