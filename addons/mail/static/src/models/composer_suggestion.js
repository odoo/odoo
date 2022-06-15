/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { sprintf } from '@web/core/utils/strings';

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
         * @param {Event} ev
         */
        onClick(ev) {
            ev.preventDefault();
            this.composerViewOwner.onClickSuggestion(this);
        },
         /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposerViewOwner() {
            if (this.composerViewOwnerAsExtraSuggestion) {
                return replace(this.composerViewOwnerAsExtraSuggestion);
            }
            if (this.composerViewOwnerAsMainSuggestion) {
                return replace(this.composerViewOwnerAsMainSuggestion);
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsActive() {
            if (this.composerViewOwnerAsMainSuggestion && this === this.composerViewOwnerAsMainSuggestion.activeSuggestion) {
                return true;
            }
            if (this.composerViewOwnerAsExtraSuggestion && this === this.composerViewOwnerAsExtraSuggestion.activeSuggestion) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeMentionText() {
            if (this.cannedResponse) {
                return this.cannedResponse.substitution;
            }
            if (this.channelCommand) {
                return this.channelCommand.name;
            }
            if (this.partner) {
                return this.partner.name;
            }
            if (this.thread) {
                return this.thread.name;
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePersonaImStatusIconView() {
            return this.partner && this.partner.isImStatusSet ? insertAndReplace() : clear();
        },
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
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeTitle() {
            if (this.cannedResponse) {
                return sprintf("%s: %s", this.record.source, this.record.substitution);
            }
            if (this.thread) {
                return this.record.name;
            }
            if (this.channelCommand) {
                return sprintf("%s: %s", this.record.name, this.record.help);
            }
            if (this.partner) {
                if (this.record.email) {
                    return sprintf("%s (%s)", this.record.nameOrDisplayName, this.record.email);
                }
                return this.record.nameOrDisplayName;
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
        composerViewOwner: one('ComposerView', {
            compute: '_computeComposerViewOwner',
            required: true,
        }),
        composerViewOwnerAsExtraSuggestion: one('ComposerView', {
            inverse: 'extraSuggestions',
            readonly: true,
        }),
        composerViewOwnerAsMainSuggestion: one('ComposerView', {
            inverse: 'mainSuggestions',
            readonly: true,
        }),
        isActive: attr({
            compute: '_computeIsActive',
            default: false,
        }),
        /**
         * The text that identifies this suggestion in a mention.
         */
        mentionText: attr({
            compute: '_computeMentionText',
        }),
        record: one('Record', {
            compute: '_computeRecord',
        }),
        partner: one('Partner', {
            readonly: true,
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'composerSuggestionViewOwner',
            isCausal: true,
            readonly: true,
        }),
        thread: one('Thread', {
            readonly: true,
        }),
        /**
         * Descriptive title for this suggestion. Useful to be able to
         * read both parts when they are overflowing the UI.
         */
        title: attr({
            compute: '_computeTitle',
            default: "",
        }),
    },
});
