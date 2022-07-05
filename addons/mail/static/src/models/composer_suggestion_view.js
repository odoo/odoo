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
    name: 'ComposerSuggestionView',
    identifyingFields: [['composerSuggestionListViewOwnerAsExtraSuggestion', 'composerSuggestionListViewOwnerAsMainSuggestion'], 'suggestable'],
    recordMethods: {
        /**
         * @param {Event} ev
         */
        onClick(ev) {
            ev.preventDefault();
            this.composerViewOwner.update({ activeSuggestionView: replace(this) });
            this.composerViewOwner.insertSuggestion();
            this.composerViewOwner.closeSuggestions();
            this.composerViewOwner.update({ doFocus: true });
        },
         /**
         * @private
         * @returns {FieldCommand}
         */
        _computeComposerViewOwner() {
            if (this.composerSuggestionListViewOwnerAsExtraSuggestion) {
                return replace(this.composerSuggestionListViewOwnerAsExtraSuggestion.composerViewOwner);
            }
            if (this.composerSuggestionListViewOwnerAsMainSuggestion) {
                return replace(this.composerSuggestionListViewOwnerAsMainSuggestion.composerViewOwner);
            }
            return clear();
        },
        /**
         * @private
         * @returns {boolean|FieldCommand}
         */
        _computeIsActive() {
            if (this.composerSuggestionListViewOwnerAsMainSuggestion && this === this.composerSuggestionListViewOwnerAsMainSuggestion.composerViewOwner.activeSuggestionView) {
                return true;
            }
            if (this.composerSuggestionListViewOwnerAsExtraSuggestion && this === this.composerSuggestionListViewOwnerAsExtraSuggestion.composerViewOwner.activeSuggestionView) {
                return true;
            }
            return clear();
        },
        /**
         * @private
         * @returns {string}
         */
        _computeMentionText() {
            if (this.suggestable.cannedResponse) {
                return this.suggestable.cannedResponse.substitution;
            }
            if (this.suggestable.channelCommand) {
                return this.suggestable.channelCommand.name;
            }
            if (this.suggestable.partner) {
                return this.suggestable.partner.name;
            }
            if (this.suggestable.thread) {
                return this.suggestable.thread.name;
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computePersonaImStatusIconView() {
            return this.suggestable.partner && this.suggestable.partner.isImStatusSet ? insertAndReplace() : clear();
        },
        /**
         * @private
         * @returns {string|FieldCommand}
         */
        _computeTitle() {
            if (this.suggestable.cannedResponse) {
                return sprintf("%s: %s", this.suggestable.cannedResponse.source, this.suggestable.cannedResponse.substitution);
            }
            if (this.suggestable.thread) {
                return this.suggestable.thread.name;
            }
            if (this.suggestable.channelCommand) {
                return sprintf("%s: %s", this.suggestable.channelCommand.name, this.suggestable.channelCommand.help);
            }
            if (this.suggestable.partner) {
                if (this.suggestable.partner.email) {
                    return sprintf("%s (%s)", this.suggestable.partner.nameOrDisplayName, this.suggestable.partner.email);
                }
                return this.suggestable.partner.nameOrDisplayName;
            }
            return clear();
        },
    },
    fields: {
        composerViewOwner: one('ComposerView', {
            compute: '_computeComposerViewOwner',
            required: true,
        }),
        composerSuggestionListViewOwnerAsExtraSuggestion: one('ComposerSuggestionListView', {
            inverse: 'extraSuggestionViews',
            readonly: true,
        }),
        composerSuggestionListViewOwnerAsMainSuggestion: one('ComposerSuggestionListView', {
            inverse: 'mainSuggestionViews',
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
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute: '_computePersonaImStatusIconView',
            inverse: 'composerSuggestionViewOwner',
            isCausal: true,
            readonly: true,
        }),
        suggestable: one('ComposerSuggestable', {
            inverse: 'composerSuggestionViews',
            readonly: true,
            required: true,
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
