/** @odoo-module **/

import { one, registerModel } from '@mail/model';

registerModel({
    name: 'ComposerSuggestedRecipientView',
    fields: {
        composerSuggestedRecipientListViewOwner: one('ComposerSuggestedRecipientListView', { identifying: true, inverse: 'composerSuggestedRecipientViews' }),
        suggestedRecipientInfo: one('SuggestedRecipientInfo', { identifying: true, inverse: 'composerSuggestedRecipientViews' }),
    },
});
