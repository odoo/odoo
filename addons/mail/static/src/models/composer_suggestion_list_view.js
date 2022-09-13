/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';

registerModel({
    name: 'ComposerSuggestionListView',
    recordMethods: {
        /**
         * Sets the first suggestion as active. Main and extra records are
         * considered together.
         */
        setFirstSuggestionViewActive() {
            const firstSuggestionView = this.suggestionViews[0];
            this.update({ rawActiveSuggestionView: firstSuggestionView });
        },
        /**
         * Sets the last suggestion as active. Main and extra records are
         * considered together.
         */
        setLastSuggestionViewActive() {
            const { length, [length - 1]: lastSuggestionView } = this.suggestionViews;
            this.update({ rawActiveSuggestionView: lastSuggestionView });
        },
        /**
         * Sets the next suggestion as active. Main and extra records are
         * considered together.
         */
        setNextSuggestionViewActive() {
            const activeElementIndex = this.suggestionViews.findIndex(
                suggestion => suggestion === this.activeSuggestionView
            );
            if (activeElementIndex === this.suggestionViews.length - 1) {
                // loop when reaching the end of the list
                this.setFirstSuggestionViewActive();
                return;
            }
            const nextSuggestionView = this.suggestionViews[activeElementIndex + 1];
            this.update({ rawActiveSuggestionView: nextSuggestionView });
        },
        /**
         * Sets the previous suggestion as active. Main and extra records are
         * considered together.
         */
        setPreviousSuggestionViewActive() {
            const activeElementIndex = this.suggestionViews.findIndex(
                suggestion => suggestion === this.activeSuggestionView
            );
            if (activeElementIndex === 0) {
                // loop when reaching the start of the list
                this.setLastSuggestionViewActive();
                return;
            }
            const previousSuggestionView = this.suggestionViews[activeElementIndex - 1];
            this.update({ rawActiveSuggestionView: previousSuggestionView });
        },
        /**
         * Adapts the active suggestion it if the active suggestion is no longer
         * part of the suggestions.
         *
         * @private
         * @returns {FieldCommand}
         */
        _computeActiveSuggestionView() {
            if (this.suggestionViews.includes(this.rawActiveSuggestionView)) {
                return this.rawActiveSuggestionView;
            }
            const firstSuggestionView = this.suggestionViews[0];
            return firstSuggestionView;
        },
        /**
         * @returns {FieldCommand}
         */
        _computeComposerSuggestionListViewExtraComposerSuggestionViewItems() {
            return this.composerViewOwner.extraSuggestions.map(suggestable => ({ suggestable }));
        },
        /**
         * @returns {FieldCommand}
         */
        _computeComposerSuggestionListViewMainComposerSuggestionViewItems() {
            return this.composerViewOwner.mainSuggestions.map(suggestable => ({ suggestable }));
        },
        /**
         * @returns {FieldCommand}
         */
        _computeSuggestionViews() {
            const mainSuggestionViews = this.composerSuggestionListViewMainComposerSuggestionViewItems.map(item => item.composerSuggestionView);
            const extraSuggestionViews = this.composerSuggestionListViewExtraComposerSuggestionViewItems.map(item => item.composerSuggestionView);
            return mainSuggestionViews.concat(extraSuggestionViews);
        },
    },
    fields: {
        /**
         * Determines the suggestion that is currently active. This suggestion
         * is highlighted in the UI and it will be selected when the
         * suggestion is confirmed by the user.
         */
        activeSuggestionView: one('ComposerSuggestionView', {
            compute: '_computeActiveSuggestionView',
            inverse: 'composerSuggestionListViewOwnerAsActiveSuggestionView',
        }),
        composerSuggestionListViewExtraComposerSuggestionViewItems: many('ComposerSuggestionListViewExtraComposerSuggestionViewItem', {
            compute: '_computeComposerSuggestionListViewExtraComposerSuggestionViewItems',
            inverse: 'composerSuggestionListViewOwner',
        }),
        composerSuggestionListViewMainComposerSuggestionViewItems: many('ComposerSuggestionListViewMainComposerSuggestionViewItem', {
            compute: '_computeComposerSuggestionListViewMainComposerSuggestionViewItems',
            inverse: 'composerSuggestionListViewOwner',
        }),
        composerViewOwner: one('ComposerView', {
            identifying: true,
            inverse: 'composerSuggestionListView',
        }),
        /**
         * Determines whether the currently active suggestion should be scrolled
         * into view.
         */
        hasToScrollToActiveSuggestionView: attr({
            default: false,
        }),
        rawActiveSuggestionView: one('ComposerSuggestionView'),
        suggestionViews: many('ComposerSuggestionView', {
            compute: '_computeSuggestionViews',
        })
    },
});
