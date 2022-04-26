/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestionListView',
    identifyingFields: ['composerViewOwner'],
    fields: {
        composerViewOwner: one('ComposerView', {
            inverse: 'composerSuggestionListView',
            readonly: true,
            required: true,
        }),
    },
});
