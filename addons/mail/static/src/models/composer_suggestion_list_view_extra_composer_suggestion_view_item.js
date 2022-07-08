/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

/**
 * Models a relation between a ComposerSuggestionListView and a
 * ComposerSuggestionView where suggestable is used as iterating field for extra
 * suggestions.
 */
registerModel({
    name: 'ComposerSuggestionListViewExtraComposerSuggestionViewItem',
    identifyingFields: ['composerSuggestionListViewOwner', 'suggestable'],
    fields: {
        composerSuggestionListViewOwner: one('ComposerSuggestionListView', {
            inverse: 'composerSuggestionListViewExtraComposerSuggestionViewItems',
            readonly: true,
            required: true,
        }),
        composerSuggestionView: one('ComposerSuggestionView', {
            default: insertAndReplace(),
            inverse: 'composerSuggestionListViewExtraComposerSuggestionViewItemOwner',
            isCausal: true,
            readonly: true,
            required: true,
        }),
        suggestable: one('ComposerSuggestable', {
            inverse: 'composerSuggestionListViewExtraComposerSuggestionViewItems',
            readonly: true,
            required: true,
        }),
    },
});
