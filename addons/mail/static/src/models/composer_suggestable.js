/** @odoo-module **/

import { many, one, Model } from "@mail/model";

Model({
    name: "ComposerSuggestable",
    identifyingMode: "xor",
    fields: {
        cannedResponse: one("CannedResponse", { identifying: true, inverse: "suggestable" }),
        channelCommand: one("ChannelCommand", { identifying: true, inverse: "suggestable" }),
        composerSuggestionListViewExtraComposerSuggestionViewItems: many(
            "ComposerSuggestionListViewExtraComposerSuggestionViewItem",
            { inverse: "suggestable" }
        ),
        composerSuggestionListViewMainComposerSuggestionViewItems: many(
            "ComposerSuggestionListViewMainComposerSuggestionViewItem",
            { inverse: "suggestable" }
        ),
        partner: one("Partner", { identifying: true, inverse: "suggestable" }),
        thread: one("Thread", { identifying: true, inverse: "suggestable" }),
    },
});
