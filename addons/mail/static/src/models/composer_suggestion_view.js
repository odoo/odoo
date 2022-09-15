/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { sprintf } from '@web/core/utils/strings';

/**
 * Models a suggestion in the composer suggestion.
 *
 * For instance, to mention a partner, can type "@" and some keyword,
 * and display suggested partners to mention.
 */
registerModel({
    name: 'ComposerSuggestionView',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @param {Event} ev
         */
        onClick(ev) {
            ev.preventDefault();
            this.composerSuggestionListViewOwner.update({ rawActiveSuggestionView: this });
            const composerViewOwner = this.composerSuggestionListViewOwner.composerViewOwner;
            composerViewOwner.insertSuggestion();
            composerViewOwner.closeSuggestions();
            composerViewOwner.update({ doFocus: true });
        },
    },
    fields: {
        composerSuggestionListViewOwner: one('ComposerSuggestionListView', {
            compute() {
                if (this.composerSuggestionListViewExtraComposerSuggestionViewItemOwner) {
                    return this.composerSuggestionListViewExtraComposerSuggestionViewItemOwner.composerSuggestionListViewOwner;
                }
                if (this.composerSuggestionListViewMainComposerSuggestionViewItemOwner) {
                    return this.composerSuggestionListViewMainComposerSuggestionViewItemOwner.composerSuggestionListViewOwner;
                }
                return clear();
            },
            required: true,
        }),
        composerSuggestionListViewOwnerAsActiveSuggestionView: one('ComposerSuggestionListView', {
            inverse: 'activeSuggestionView',
        }),
        composerSuggestionListViewExtraComposerSuggestionViewItemOwner: one('ComposerSuggestionListViewExtraComposerSuggestionViewItem', {
            identifying: true,
            inverse: 'composerSuggestionView',
        }),
        composerSuggestionListViewMainComposerSuggestionViewItemOwner: one('ComposerSuggestionListViewMainComposerSuggestionViewItem', {
            identifying: true,
            inverse: 'composerSuggestionView',
        }),
        /**
         * The text that identifies this suggestion in a mention.
         */
        mentionText: attr({
            compute() {
                if (!this.suggestable) {
                    return clear();
                }
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
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', {
            compute() {
                return this.suggestable && this.suggestable.partner && this.suggestable.partner.isImStatusSet ? {} : clear();
            },
            inverse: 'composerSuggestionViewOwner',
        }),
        suggestable: one('ComposerSuggestable', {
            compute() {
                if (this.composerSuggestionListViewExtraComposerSuggestionViewItemOwner) {
                    return this.composerSuggestionListViewExtraComposerSuggestionViewItemOwner.suggestable;
                }
                if (this.composerSuggestionListViewMainComposerSuggestionViewItemOwner) {
                    return this.composerSuggestionListViewMainComposerSuggestionViewItemOwner.suggestable;
                }
                return clear();
            },
            required: true,
        }),
        /**
         * Descriptive title for this suggestion. Useful to be able to
         * read both parts when they are overflowing the UI.
         */
        title: attr({
            compute() {
                if (!this.suggestable) {
                    return clear();
                }
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
            default: "",
        }),
    },
});
