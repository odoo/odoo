/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestedRecipientView',
    fields: {
        composerSuggestedRecipientListViewOwner: one('ComposerSuggestedRecipientListView', {
            identifying: true,
            inverse: 'composerSuggestedRecipientViews',
        }),
        suggestedRecipientInfo: one('SuggestedRecipientInfo', {
            identifying: true,
            inverse: 'composerSuggestedRecipientViews',
        }),
    },
});
