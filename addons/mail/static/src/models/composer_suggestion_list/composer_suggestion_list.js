/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { clear, link, unlink, unlinkAll } from '@mail/model/model_field_command';
import { attr, one2one, many2one, many2many } from '@mail/model/model_field';

function factory(dependencies) {

    class ComposerSuggestionList extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------
        /**
         * Closes the suggestion list.
         */
        closeSuggestions() {
            this.composer.update({ suggestionDelimiterPosition: clear() });
        }

        /**
         * Sets the first suggestion as active. Main and extra records are
         * considered together.
         */
        setFirstSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const firstRecord = suggestedRecords[0];
            this.update({ activeSuggestedRecord: link(firstRecord) });
        }

        /**
         * Sets the last suggestion as active. Main and extra records are
         * considered together.
         */
        setLastSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const { length, [length - 1]: lastRecord } = suggestedRecords;
            this.update({ activeSuggestedRecord: link(lastRecord) });
        }

        /**
         * Sets the next suggestion as active. Main and extra records are
         * considered together.
         */
        setNextSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const activeElementIndex = suggestedRecords.findIndex(
                suggestion => suggestion === this.activeSuggestedRecord
            );
            if (activeElementIndex === suggestedRecords.length - 1) {
                // loop when reaching the end of the list
                this.setFirstSuggestionActive();
                return;
            }
            const nextRecord = suggestedRecords[activeElementIndex + 1];
            this.update({ activeSuggestedRecord: link(nextRecord) });
        }

        /**
         * Sets the previous suggestion as active. Main and extra records are
         * considered together.
         */
        setPreviousSuggestionActive() {
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const activeElementIndex = suggestedRecords.findIndex(
                suggestion => suggestion === this.activeSuggestedRecord
            );
            if (activeElementIndex === 0) {
                // loop when reaching the start of the list
                this.setLastSuggestionActive();
                return;
            }
            const previousRecord = suggestedRecords[activeElementIndex - 1];
            this.update({ activeSuggestedRecord: link(previousRecord) });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Clears the active suggested record on closing mentions or adapt it if
         * the active current record is no longer part of the suggestions.
         *
         * @private
         * @returns {mail.model}
         */
        _computeActiveSuggestedRecord() {
            if (
                this.mainSuggestedRecords.length === 0 &&
                this.extraSuggestedRecords.length === 0
            ) {
                return unlink();
            }
            if (
                this.mainSuggestedRecords.includes(this.activeSuggestedRecord) ||
                this.extraSuggestedRecords.includes(this.activeSuggestedRecord)
            ) {
                return;
            }
            const suggestedRecords = this.mainSuggestedRecords.concat(this.extraSuggestedRecords);
            const firstRecord = suggestedRecords[0];
            return link(firstRecord);
        }

        /**
         * Clears the main suggested record on closing mentions.
         *
         * @private
         * @returns {mail.model[]}
         */
        _computeMainSuggestedRecords() {
            if (this.composer.suggestionDelimiterPosition === undefined) {
                return unlinkAll();
            }
        }

        /**
         * Clears the extra suggested record on closing mentions, and ensures
         * the extra list does not contain any element already present in the
         * main list, which is a requirement for the navigation process.
         *
         * @private
         * @returns {mail.model[]}
         */
        _computeExtraSuggestedRecords() {
            if (this.composer.suggestionDelimiterPosition === undefined) {
                return unlinkAll();
            }
            return unlink(this.mainSuggestedRecords);
        }

        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestions() {
            return this.mainSuggestedRecords.length > 0 || this.extraSuggestedRecords.length > 0;
        }

    }

    ComposerSuggestionList.fields = {
        composer: one2one('mail.composer', {
            inverse: 'composerSuggestionList',
        }),
        composerSuggestionDelimiterPosition: attr({
            related: 'composer.suggestionDelimiterPosition',
        }),
        /**
         * Determines the suggested record that is currently active. This record
         * is highlighted in the UI and it will be the selected record if the
         * suggestion is confirmed by the user.
         */
        activeSuggestedRecord: many2one('mail.model', {
            compute: '_computeActiveSuggestedRecord',
            dependencies: [
                'activeSuggestedRecord',
                'extraSuggestedRecords',
                'mainSuggestedRecords',
            ],
        }),
        /**
         * Determines the extra records that are currently suggested.
         * Allows to have different model types of mentions through a dynamic
         * process. 2 arbitrary lists can be provided and the second is defined
         * as "extra".
         */
        extraSuggestedRecords: many2many('mail.model', {
            compute: '_computeExtraSuggestedRecords',
            dependencies: [
                'extraSuggestedRecords',
                'mainSuggestedRecords',
                'composerSuggestionDelimiterPosition',
            ],
        }),
        /**
         * Determines the main records that are currently suggested.
         * Allows to have different model types of mentions through a dynamic
         * process. 2 arbitrary lists can be provided and the first is defined
         * as "main".
         */
        mainSuggestedRecords: many2many('mail.model', {
            compute: '_computeMainSuggestedRecords',
            dependencies: [
                'mainSuggestedRecords',
                'composerSuggestionDelimiterPosition',
            ],
        }),
        /**
         * States whether there is any result currently found for the current
         * suggestion delimiter and search term, if applicable.
         */
        hasSuggestions: attr({
            compute: '_computeHasSuggestions',
            dependencies: [
                'extraSuggestedRecords',
                'mainSuggestedRecords',
            ],
            default: false,
        }),
    };

    ComposerSuggestionList.modelName = 'mail.composer_suggestion_list';

    return ComposerSuggestionList;
}

registerNewModel('mail.composer_suggestion_list', factory);
