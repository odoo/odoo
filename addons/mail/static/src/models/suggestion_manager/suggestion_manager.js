odoo.define('mail/static/src/models/suggestion_manager/suggestion_manager.js', function (require) {
'use strict';

const { registerNewModel } = require('mail/static/src/model/model_core.js');
const { attr, many2many, many2one, one2one } = require('mail/static/src/model/model_field.js');
const { clear, link, replace, unlink, unlinkAll } = require('mail/static/src/model/model_field_command.js');

function factory(dependencies) {

    class SuggestionManager extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * Closes the suggestion list.
         */
        closeSuggestions() {
            this.update({ suggestionDelimiterPosition: clear() });
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
         * Executes the given async function, only when the last function
         * executed by this method terminates. If there is already a pending
         * function it is replaced by the new one. This ensures the result of
         * these function come in the same order as the call order, and it also
         * allows to skip obsolete intermediate calls.
         *
         * @private
         * @param {function} func
         */
        async _executeOrQueueFunction(func) {
            if (this._hasMentionRpcInProgress) {
                this._nextMentionRpcFunction = func;
                return;
            }
            this._hasMentionRpcInProgress = true;
            this._nextMentionRpcFunction = undefined;
            try {
                await this.async(func);
            } finally {
                this._hasMentionRpcInProgress = false;
                if (this._nextMentionRpcFunction) {
                    this._executeOrQueueFunction(this._nextMentionRpcFunction);
                }
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
            if (this.suggestionDelimiterPosition === undefined) {
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

        /**
         * Clears the main suggested record on closing mentions.
         *
         * @private
         * @returns {mail.model[]}
         */
        _computeMainSuggestedRecords() {
            if (this.suggestionDelimiterPosition === undefined) {
                return unlinkAll();
            }
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionDelimiter() {
            if (
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.textInputContent.length
            ) {
                return clear();
            }
            return this.textInputContent[this.suggestionDelimiterPosition];
        }

        /**
         * @private
         * @returns {integer}
         */
        _computeSuggestionDelimiterPosition() {
            if (this.textInputCursorStart !== this.textInputCursorEnd) {
                // avoid interfering with multi-char selection
                return clear();
            }
            const candidatePositions = [];
            // keep the current delimiter if it is still valid
            if (
                this.suggestionDelimiterPosition !== undefined &&
                this.suggestionDelimiterPosition < this.textInputCursorStart
            ) {
                candidatePositions.push(this.suggestionDelimiterPosition);
            }
            // consider the char before the current cursor position if the
            // current delimiter is no longer valid (or if there is none)
            if (this.textInputCursorStart > 0) {
                candidatePositions.push(this.textInputCursorStart - 1);
            }
            const suggestionDelimiters = ['@', ':', '#', '/'];
            for (const candidatePosition of candidatePositions) {
                if (
                    candidatePosition < 0 ||
                    candidatePosition >= this.textInputContent.length
                ) {
                    continue;
                }
                const candidateChar = this.textInputContent[candidatePosition];
                if (candidateChar === '/' && candidatePosition !== 0) {
                    continue;
                }
                if (!suggestionDelimiters.includes(candidateChar)) {
                    continue;
                }
                const charBeforeCandidate = this.textInputContent[candidatePosition - 1];
                if (charBeforeCandidate && !/\s/.test(charBeforeCandidate)) {
                    continue;
                }
                return candidatePosition;
            }
            return clear();
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionModelName() {
            switch (this.suggestionDelimiter) {
                case '@':
                    return 'mail.partner';
                case ':':
                    return 'mail.canned_response';
                case '/':
                    return 'mail.channel_command';
                case '#':
                    return 'mail.thread';
                default:
                    return clear();
            }
        }

        /**
         * @private
         * @returns {string}
         */
        _computeSuggestionSearchTerm() {
            if (
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionDelimiterPosition >= this.textInputCursorStart
            ) {
                return clear();
            }
            return this.textInputContent.substring(this.suggestionDelimiterPosition + 1, this.textInputCursorStart);
        }

        /**
         * Updates the suggestion state based on the currently saved composer
         * state (in particular content and cursor position).
         *
         * @private
         */
        _onChangeUpdateSuggestionList() {
            // Update the suggestion list immediately for a reactive UX...
            this._updateSuggestionList();
            // ...and then update it again after the server returned data.
            this._executeOrQueueFunction(async () => {
                if (
                    this.suggestionDelimiterPosition === undefined ||
                    this.suggestionSearchTerm === undefined ||
                    !this.suggestionModelName
                ) {
                    // ignore obsolete call
                    return;
                }
                const Model = this.env.models[this.suggestionModelName];
                const searchTerm = this.suggestionSearchTerm;
                await this.async(() => Model.fetchSuggestions(searchTerm, { thread: this.thread }));
                this._updateSuggestionList();
                if (
                    this.suggestionSearchTerm &&
                    this.suggestionSearchTerm === searchTerm &&
                    this.suggestionModelName &&
                    this.env.models[this.suggestionModelName] === Model &&
                    !this.hasSuggestions
                ) {
                    this.closeSuggestions();
                }
            });
        }

        /**
         * Updates the current suggestion list. This method should be called
         * whenever the UI has to be refreshed following change in state.
         *
         * This method should ideally be a compute, but its dependencies are
         * currently too complex to express due to accessing plenty of fields
         * from all records of dynamic models.
         *
         * @private
         */
        _updateSuggestionList() {
            if (
                this.suggestionDelimiterPosition === undefined ||
                this.suggestionSearchTerm === undefined ||
                !this.suggestionModelName
            ) {
                return;
            }
            const Model = this.env.models[this.suggestionModelName];
            const [
                mainSuggestedRecords,
                extraSuggestedRecords = [],
            ] = Model.searchSuggestions(this.suggestionSearchTerm, { thread: this.thread });
            const sortFunction = Model.getSuggestionSortFunction(this.suggestionSearchTerm, { thread: this.thread });
            mainSuggestedRecords.sort(sortFunction);
            extraSuggestedRecords.sort(sortFunction);
            // arbitrary limit to avoid displaying too many elements at once
            // ideally a load more mechanism should be introduced
            const limit = 8;
            mainSuggestedRecords.length = Math.min(mainSuggestedRecords.length, limit);
            extraSuggestedRecords.length = Math.min(extraSuggestedRecords.length, limit - mainSuggestedRecords.length);
            this.update({
                extraSuggestedRecords: replace(extraSuggestedRecords),
                hasToScrollToActiveSuggestion: true,
                mainSuggestedRecords: replace(mainSuggestedRecords),
            });
        }

    }

    SuggestionManager.fields = {
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
        activeSuggestedRecordName: attr({
            default: "",
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
                'suggestionDelimiterPosition',
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
        /**
         * Determines whether the currently active suggestion should be scrolled
         * into view.
         */
        hasToScrollToActiveSuggestion: attr({
            default: false,
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
                'suggestionDelimiterPosition',
            ],
        }),
        /**
         * Not a real field, used to trigger `_onChangeUpdateSuggestionList`
         * when one of the dependencies changes.
         */
        onChangeUpdateSuggestionList: attr({
            compute: '_onChangeUpdateSuggestionList',
            dependencies: [
                'suggestionDelimiterPosition',
                'suggestionModelName',
                'suggestionSearchTerm',
                'thread',
            ],
        }),
        /**
         * States which type of suggestion is currently in progress, if any.
         * The value of this field contains the magic char that corresponds to
         * the suggestion currently in progress, and it must be one of these:
         * canned responses (:), channels (#), commands (/) and partners (@)
         */
        suggestionDelimiter: attr({
            compute: '_computeSuggestionDelimiter',
            dependencies: [
                'suggestionDelimiterPosition',
                'textInputContent',
            ],
        }),
        /**
         * States the position inside textInputContent of the suggestion
         * delimiter currently in consideration. Useful if the delimiter char
         * appears multiple times in the content.
         * Note: the position is 0 based so it's important to compare to
         * `undefined` when checking for the absence of a value.
         */
        suggestionDelimiterPosition: attr({
            compute: '_computeSuggestionDelimiterPosition',
            dependencies: [
                'textInputContent',
                'textInputCursorEnd',
                'textInputCursorStart',
            ],
        }),
        /**
         * States the target model name of the suggestion currently in progress,
         * if any.
         */
        suggestionModelName: attr({
            compute: '_computeSuggestionModelName',
            dependencies: [
                'suggestionDelimiter',
            ],
        }),
        /**
         * States the search term to use for suggestions (if any).
         */
        suggestionSearchTerm: attr({
            compute: '_computeSuggestionSearchTerm',
            dependencies: [
                'suggestionDelimiterPosition',
                'textInputContent',
                'textInputCursorStart',
            ],
        }),
        /**
         * This will contain the text to analyse
         */
        textInputContent: attr({
            default: "",
        }),
        textInputCursorEnd: attr({
            default: 0,
        }),
        textInputCursorStart: attr({
            default: 0,
        }),
        thread: one2one('mail.thread'),
    };

    SuggestionManager.modelName = 'mail.suggestionManager';

    return SuggestionManager;
}

registerNewModel('mail.suggestionManager', factory);

});
