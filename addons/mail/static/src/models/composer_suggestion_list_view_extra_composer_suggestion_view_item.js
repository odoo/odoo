/** @odoo-module **/

import { one, Model } from "@mail/model";

/**
 * Models a relation between a ComposerSuggestionListView and a
 * ComposerSuggestionView where suggestable is used as iterating field for extra
 * suggestions.
 */
Model({
    name: "ComposerSuggestionListViewExtraComposerSuggestionViewItem",
    fields: {
        composerSuggestionListViewOwner: one("ComposerSuggestionListView", {
            identifying: true,
            inverse: "composerSuggestionListViewExtraComposerSuggestionViewItems",
        }),
        composerSuggestionView: one("ComposerSuggestionView", {
            default: {},
            inverse: "composerSuggestionListViewExtraComposerSuggestionViewItemOwner",
            readonly: true,
            required: true,
        }),
        suggestable: one("ComposerSuggestable", {
            identifying: true,
            inverse: "composerSuggestionListViewExtraComposerSuggestionViewItems",
        }),
    },
});
