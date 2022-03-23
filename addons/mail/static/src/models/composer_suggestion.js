/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

/**
 * Models a suggestion in the composer suggestion.
 *
 * For instance, to mention a partner, can type "@" and some keyword,
 * and display suggested partners to mention.
 */
registerModel({
    name: 'ComposerSuggestion',
    identifyingFields: [['composerViewOwnerAsExtraSuggestion', 'composerViewOwnerAsMainSuggestion'], ['cannedResponse', 'channelCommand', 'partner', 'thread']],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeRecord() {
            if (this.cannedResponse) {
                return replace(this.cannedResponse);
            }
            if (this.channelCommand) {
                return replace(this.channelCommand);
            }
            if (this.partner) {
                return replace(this.partner);
            }
            if (this.thread) {
                return replace(this.thread);
            }
            return clear();
        },
    },
    fields: {
        cannedResponse: one('CannedResponse', {
            readonly: true,
        }),
        channelCommand: one('ChannelCommand', {
            readonly: true,
        }),
        composerViewOwnerAsExtraSuggestion: one('ComposerView', {
            inverse: 'extraSuggestions',
            readonly: true,
        }),
        composerViewOwnerAsMainSuggestion: one('ComposerView', {
            inverse: 'mainSuggestions',
            readonly: true,
        }),
        record: one('Record', {
            compute: '_computeRecord',
        }),
        partner: one('Partner', {
            readonly: true,
        }),
        thread: one('Thread', {
            readonly: true,
        }),
    },
});
