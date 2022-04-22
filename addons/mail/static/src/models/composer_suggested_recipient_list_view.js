/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestedRecipientListView',
    identifyingFields: ['composerViewOwner'],
    fields: {
        composerViewOwner: one('ComposerView', {
            inverse: 'composerSuggestedRecipientListView',
            readonly: true,
            required: true,
        }),
    },
});
