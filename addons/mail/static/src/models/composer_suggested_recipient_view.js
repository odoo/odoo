/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestedRecipientView',
    identifyingFields: ['composerSuggestedRecipientListViewOwner', 'suggestedRecipientInfo'],
    fields: {
        composerSuggestedRecipientListViewOwner: one('ComposerSuggestedRecipientListView', {
            inverse: 'composerSuggestedRecipientViews',
            readonly: true,
            required: true,
        }),
        suggestedRecipientInfo: one('SuggestedRecipientInfo', {
            inverse: 'composerSuggestedRecipientViews',
            readonly: true,
            required: true,
        }),
    },
});
