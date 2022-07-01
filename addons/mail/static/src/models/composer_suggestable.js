/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestable',
    identifyingFields: [['cannedResponse', 'channelCommand', 'partner', 'thread']],
    fields: {
        cannedResponse: one('CannedResponse', {
            inverse: 'suggestable',
            readonly: true,
        }),
        channelCommand: one('ChannelCommand', {
            inverse: 'suggestable',
            readonly: true,
        }),
        composerSuggestions: many('ComposerSuggestion', {
            inverse: 'suggestable',
            isCausal: true,
        }),
        partner: one('Partner', {
            inverse: 'suggestable',
            readonly: true,
        }),
        thread: one('Thread', {
            inverse: 'suggestable',
            readonly: true,
        }),
    },
});
