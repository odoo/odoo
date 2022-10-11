/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'DiscussMobileMailboxSelectionView',
    fields: {
        owner: one('DiscussView', {
            identifying: true,
            inverse: 'mobileMailboxSelectionView',
        }),
    },
});
