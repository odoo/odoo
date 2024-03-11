/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

/**
 * Models a relation between a ComposerSuggestionListView and a
 * ComposerSuggestionView where suggestable is used as iterating field for main
 * suggestions.
 */
registerModel({
    name: 'ComposerSuggestionListViewMainComposerSuggestionViewItem',
    fields: {
        composerSuggestionListViewOwner: one('ComposerSuggestionListView', {
            identifying: true,
            inverse: 'composerSuggestionListViewMainComposerSuggestionViewItems',
        }),
        composerSuggestionView: one('ComposerSuggestionView', {
            default: {},
            inverse: 'composerSuggestionListViewMainComposerSuggestionViewItemOwner',
            readonly: true,
            required: true,
        }),
        suggestable: one('ComposerSuggestable', {
            identifying: true,
            inverse: 'composerSuggestionListViewMainComposerSuggestionViewItems',
        }),
    },
});
