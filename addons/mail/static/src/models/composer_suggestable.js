/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestable',
    identifyingMode: 'xor',
    fields: {
        cannedResponse: one('CannedResponse', {
            identifying: true,
            inverse: 'suggestable',
            readonly: true,
        }),
        channelCommand: one('ChannelCommand', {
            identifying: true,
            inverse: 'suggestable',
            readonly: true,
        }),
        composerSuggestionListViewExtraComposerSuggestionViewItems: many('ComposerSuggestionListViewExtraComposerSuggestionViewItem', {
            inverse: 'suggestable',
            isCausal: true,
        }),
        composerSuggestionListViewMainComposerSuggestionViewItems: many('ComposerSuggestionListViewMainComposerSuggestionViewItem', {
            inverse: 'suggestable',
            isCausal: true,
        }),
        partner: one('Partner', {
            identifying: true,
            inverse: 'suggestable',
            readonly: true,
        }),
        thread: one('Thread', {
            identifying: true,
            inverse: 'suggestable',
            readonly: true,
        }),
    },
});
