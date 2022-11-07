/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { attr, clear, one, Model } from '@mail/model';
import { sprintf } from '@web/core/utils/strings';

/**
 * Models a suggestion in the composer suggestion.
 *
 * For instance, to mention a partner, can type "@" and some keyword,
 * and display suggested partners to mention.
 */
Model({
    name: 'ComposerSuggestionView',
    template: 'mail.ComposerSuggestionView',
    componentSetup() {
        useComponentToModel({ fieldName: 'component' });
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    },
    recordMethods: {
        /**
         * @param {Event} ev
         */
        onClick(ev) {
            // ev.preventDefault();
            // this.navigableListViewAsSuggestion.update({ userExplicitSelection: this.navigableListItemView });
            // const composerView = this.navigableListViewAsSuggestion.ownerAsComposerSuggestion;
            // composerView.insertSuggestion();
            // composerView.closeSuggestions();
            // composerView.update({ doFocus: true });
        },
        onComponentUpdate() {
            // if (
            //     this.component.root.el &&
            //     this.navigableListViewAsSuggestion.hasToScrollToActiveItem &&
            //     this.navigableListViewAsSuggestion.activeItem &&
            //     this.navigableListViewAsSuggestion.activeItem.composerSuggestionViewOwner === this
            // ) {
            //     this.component.root.el.scrollIntoView({ block: 'center' });
            //     this.navigableListViewAsSuggestion.update({ hasToScrollToActiveItem: false });
            // }
        },
    },
    fields: {
        component: attr(),
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
        navigableListItemViewOwner: one('NavigableListItemView', {
            identifying: true,
            inverse: 'composerSuggestionView',
        }),
        navigableListViewAsSuggestion: one('NavigableListView', {
            compute() {
                return this.navigableListItemViewOwner.navigableListMainOrExtraItemView.navigableListViewAsSuggestion;
            },
        }),
        personaImStatusIconView: one('PersonaImStatusIconView', { inverse: 'composerSuggestionViewOwner',
            compute() {
                return this.suggestable && this.suggestable.partner && this.suggestable.partner.isImStatusSet ? {} : clear();
            },
        }),
        suggestable: one('Suggestable', {
            related: 'navigableListItemViewOwner.suggestable',
        }),
        /**
         * Descriptive title for this suggestion. Useful to be able to
         * read both parts when they are overflowing the UI.
         */
        title: attr({ default: "",
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
        }),
    },
});
