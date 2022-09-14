/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';

registerModel({
    name: 'Global',
    lifecycleHooks: {
        _created() {
            odoo.__DEBUG__.messagingGlobal = this;
        },
        _willDelete() {
            delete odoo.__DEBUG__.messagingGlobal;
        },
    },
    fields: {
        allRecords: many('Record', {
            inverse: 'global',
        }),
    },
});
