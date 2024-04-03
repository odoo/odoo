/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many } from '@mail/model/model_field';

registerModel({
    name: 'PopoverManager',
    fields: {
        // FIXME: dependent on implementation that uses insert order in relations!!
        popoverViews: many('PopoverView', {
            inverse: 'manager',
            isCausal: true,
        }),
    },
});
