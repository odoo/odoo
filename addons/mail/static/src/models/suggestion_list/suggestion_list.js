/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { link, replace, unlink, update } from '@mail/model/model_field_command';
import { attr, many2one, one2many, one2one } from '@mail/model/model_field';
import { markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class SuggestionList extends dependencies['mail.model'] {

        /**
         * @override
         */
        _willCreate() {
            const res = super._willCreate(...arguments);
            /**
             * Determines whether there is a mention RPC currently in progress.
             * Useful to queue a new call if there is already one pending.
             */
            this._hasMentionRpcInProgress = false;
            /**
             * Determines the next function to execute after the current mention
             * RPC is done, if any.
             */
            this._nextMentionRpcFunction = undefined;
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            // Clears the mention queue on deleting this suggestion list to
            // prevent unnecessary RPC.
            this._nextMentionRpcFunction = undefined;
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------


        /**
         * Handles keydown event from whichever element has focus and decided to
         * forward its event to this suggestion list.
         */
        onKeydown(ev) {
            if (!this.hasSuggestions) {
                return;
            }
            switch (ev.key) {
                case 'Enter':
                    if (this.onSuggestionSelected) {
                        this.onSuggestionSelected(this.activeSuggestionListItem.record);
                    }
                    markEventHandled(ev, 'SuggestionList.suggestionSelected');
                    break;
                case 'Escape':
                    if (this.onSuggestionListClosed) {
                        this.onSuggestionListClosed();
                    }
                    markEventHandled(ev, 'SuggestionList.suggestionListClosed');
                    break;
                case 'ArrowUp':
                case 'PageUp':
                    this.setPreviousSuggestionActive();
                    markEventHandled(ev, 'SuggestionList.navigationUp');
                    break;
                case 'ArrowDown':
                case 'PageDown':
                    this.setNextSuggestionActive();
                    markEventHandled(ev, 'SuggestionList.navigationDown');
                    break;
                case 'Home':
                    this.setFirstSuggestionActive();
                    markEventHandled(ev, 'SuggestionList.navigationTop');
                    break;
                case 'End':
                    this.setLastSuggestionActive();
                    markEventHandled(ev, 'SuggestionList.navigationBottom');
                    break;
                case 'Tab':
                    if (ev.shiftKey) {
                        this.setPreviousSuggestionActive();
                        markEventHandled(ev, 'SuggestionList.navigationUp');
                    } else {
                        this.setNextSuggestionActive();
                        markEventHandled(ev, 'SuggestionList.navigationDown');
                    }
                    break;
            }
        }

        /**
         * Sets the first suggestion list item as active. Main and extra
         * suggestion list items are considered together.
         */
        setFirstSuggestionActive() {
            const firstSuggestionListItem = this.allSuggestionListItems[0];
            this.setSuggestionListItemActive(firstSuggestionListItem);
        }

        /**
         * Sets the last suggestion list item as active. Main and extra
         * suggestion list items are considered together.
         */
        setLastSuggestionActive() {
            const { length, [length - 1]: lastSuggestionListItem } = this.allSuggestionListItems;
            this.setSuggestionListItemActive(lastSuggestionListItem);
        }

        /**
         * Sets the next suggestion list item as active. Main and extra
         * suggestion list items are considered together.
         */
        setNextSuggestionActive() {
            const activeSuggestionListItemIndex = this.allSuggestionListItems.findIndex(
                suggestion => suggestion === this.activeSuggestionListItem
            );
            if (activeSuggestionListItemIndex === this.allSuggestionListItems.length - 1) {
                // loop when reaching the end of the list
                this.setFirstSuggestionActive();
                return;
            }
            const nextSuggestionListItem = this.allSuggestionListItems[activeSuggestionListItemIndex + 1];
            this.setSuggestionListItemActive(nextSuggestionListItem);
        }

        /**
         * Sets the previous suggestion list item as active. Main and extra
         * suggestion list items are considered together.
         */
        setPreviousSuggestionActive() {
            const activeSuggestionListItemIndex = this.allSuggestionListItems.findIndex(
                suggestion => suggestion === this.activeSuggestionListItem
            );
            if (activeSuggestionListItemIndex === 0) {
                // loop when reaching the start of the list
                this.setLastSuggestionActive();
                return;
            }
            const previousSuggestionListItem = this.allSuggestionListItems[activeSuggestionListItemIndex - 1];
            this.setSuggestionListItemActive(previousSuggestionListItem);
        }

        /**
         * Sets the given suggestion list item as active and ensures it becomes
         * visible.
         *
         * @private
         * @param {mail.suggestion_list_item} suggestionListItem
         */
        setSuggestionListItemActive(suggestionListItem) {
            this.update({ activeSuggestionListItem: link(suggestionListItem) });
            this.activeSuggestionListItem.update({ hasToScrollIntoView: true });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * Adjusts the currently active suggestion list item. In particular,
         * removes the current suggestion list item from being active if it is
         * no longer part of the list, and adds the first suggestion list item
         * of the list if no other suggestion list item is currently active.
         *
         * @private
         * @returns {mail.suggestion_list_item}
         */
        _computeActiveSuggestionListItem() {
            if (this.allSuggestionListItems.length === 0) {
                return unlink();
            }
            if (this.allSuggestionListItems.includes(this.activeSuggestionListItem)) {
                return;
            }
            const firstSuggestionListItem = this.allSuggestionListItems[0];
            return link(firstSuggestionListItem);
        }

        /**
         * Computes the unified list of suggestion list items (merging together
         * main and extra) and properly updates their highlighted state
         * depending on the currently active suggestion list item.
         *
         * @private
         * @returns {mail.suggestion_list_item[]}
         */
        _computeAllSuggestionListItems() {
            // TODO SEB add a test for checking proper compute if isHighlighted
            const allSuggestionListItems = this.mainSuggestionListItems.concat(this.extraSuggestionListItems);
            const newValuesPerItem = new Map(allSuggestionListItems.map(suggestionListItem => [
                suggestionListItem,
                {
                    isHighlighted: suggestionListItem === this.activeSuggestionListItem,
                },
            ]));
            return [
                replace(allSuggestionListItems),
                update(newValuesPerItem),
            ];
        }

        /**
         * Ensures the extra list does not contain any element already present
         * in the main list, which is a requirement for the navigation process.
         *
         * @private
         * @returns {mail.suggestion_list_item[]}
         */
        _computeExtraSuggestionListItems() {
            return unlink(this.mainSuggestionListItems);
        }

        /**
         * @private
         * @return {boolean}
         */
        _computeHasSuggestions() {
            return this.allSuggestionListItems.length > 0;
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
            await func();
            this._hasMentionRpcInProgress = false;
            if (!this.exists()) {
                return;
            }
            if (this._nextMentionRpcFunction) {
                this._executeOrQueueFunction(this._nextMentionRpcFunction);
            }
        }

        /**
         * Updates this list based on this state.
         *
         * @private
         */
        _onChangeUpdateSuggestionList() {
            // Update the suggestion list immediately for a reactive UX...
            this._updateSuggestionList();
            // ...and then update it again after the server returned data.
            this._executeOrQueueFunction(async () => {
                const modelName = this.suggestionModelName;
                const searchTerm = this.suggestionSearchTerm;
                const Model = this.env.models[modelName];
                await Model.fetchSuggestions(searchTerm, { thread: this.thread });
                if (
                    !this.exists() ||
                    this.suggestionSearchTerm !== searchTerm ||
                    this.suggestionModelName !== modelName
                ) {
                    // ignore obsolete call
                    return;
                }
                this._updateSuggestionList();
                if (!this.hasSuggestions && this.onSuggestionNoResult) {
                    this.onSuggestionNoResult();
                }
            });
        }

        /**
         * @private
         * @param {mail.suggestion_list_item}
         */
        _onSuggestionClicked(suggestionListItem) {
            this.setSuggestionListItemActive(suggestionListItem);
            if (this.onSuggestionSelected) {
                this.onSuggestionSelected(suggestionListItem.record);
            }
        }

        /**
         * Maps records to suggestion list items, by trying to re-using existing
         * suggestion list items whenever possible to avoid losing the current
         * active state when the list changes.
         *
         * @private
         * @param {mail.model[]} records
         * @returns {mail.suggestion_list_item[]}
         */
        _findOrCreateSuggestionListItemsForRecords(records) {
            const suggestionListItemPerRecord = new Map(records.map(record => [record, undefined]));
            for (const suggestionListItem of this.allSuggestionListItems) {
                if (suggestionListItemPerRecord.has(suggestionListItem.record)) {
                    suggestionListItemPerRecord.set(suggestionListItem.record, suggestionListItem);
                }
            }
            for (const [record, suggestionListItem] of suggestionListItemPerRecord) {
                if (suggestionListItem) {
                    continue;
                }
                suggestionListItemPerRecord.set(record, this.env.models['mail.suggestion_list_item'].create({
                    onSuggestionClicked: suggestionListItem => this._onSuggestionClicked(suggestionListItem),
                    record: link(record),
                }));
            }
            return [...suggestionListItemPerRecord.values()];
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
            const Model = this.env.models[this.suggestionModelName];
            const [
                mainRecords,
                extraRecords = [],
            ] = Model.searchSuggestions(this.suggestionSearchTerm, { thread: this.thread });
            const sortFunction = Model.getSuggestionSortFunction(this.suggestionSearchTerm, { thread: this.thread });
            mainRecords.sort(sortFunction);
            extraRecords.sort(sortFunction);
            // arbitrary limit to avoid displaying too many elements at once
            // ideally a load more mechanism should be introduced
            const limit = 8;
            mainRecords.length = Math.min(mainRecords.length, limit);
            extraRecords.length = Math.min(extraRecords.length, limit - mainRecords.length);
            this.update({
                extraSuggestionListItems: replace(this._findOrCreateSuggestionListItemsForRecords(extraRecords)),
                mainSuggestionListItems: replace(this._findOrCreateSuggestionListItemsForRecords(mainRecords)),
            });
            if (this.activeSuggestionListItem) {
                this.activeSuggestionListItem.update({ hasToScrollIntoView: true });
            }
        }

    }

    SuggestionList.fields = {
        /**
         * Determines the suggestion list item that is currently active. It is
         * highlighted in the UI and it will be the selected suggestion list
         * item if the suggestion is confirmed by the user.
         */
        activeSuggestionListItem: one2one('mail.suggestion_list_item', {
            compute: '_computeActiveSuggestionListItem',
            dependencies: [
                'activeSuggestionListItem',
                'allSuggestionListItems',
            ],
        }),
        /**
         * States all suggestion list items that belong to this suggestion list.
         */
        allSuggestionListItems: one2many('mail.suggestion_list_item', {
            compute: '_computeAllSuggestionListItems',
            dependencies: [
                'activeSuggestionListItem',
                'extraSuggestionListItems',
                'mainSuggestionListItems',
            ],
            isCausal: true,
            readonly: true,
        }),
        /**
         * Determines the extra suggestion list items.
         * 2 arbitrary lists can be provided and the 2nd is defined as "extra".
         */
        extraSuggestionListItems: one2many('mail.suggestion_list_item', {
            compute: '_computeExtraSuggestionListItems',
            dependencies: [
                'extraSuggestionListItems',
                'mainSuggestionListItems',
            ],
        }),
        /**
         * States whether there is any result currently found for the current
         * suggestion model name and search term, if applicable.
         */
        hasSuggestions: attr({
            compute: '_computeHasSuggestions',
            dependencies: [
                'allSuggestionListItems',
            ],
            default: false,
            readonly: true,
        }),
        /**
         * Determines the main suggestion list items.
         * 2 arbitrary lists can be provided and the 1st is defined as "main".
         */
        mainSuggestionListItems: one2many('mail.suggestion_list_item'),
        /**
         * Not a real field, used to trigger `_onChangeUpdateSuggestionList`
         * when one of the dependencies changes.
         */
        onChangeUpdateSuggestionList: attr({
            compute: '_onChangeUpdateSuggestionList',
            dependencies: [
                'suggestionModelName',
                'suggestionSearchTerm',
                'thread',
            ],
            isOnChange: true,
        }),
        /**
         * Determines the function to execute when no results have been found
         * for the current search model name and search term. The function is
         * called with no parameter.
         */
        onSuggestionNoResult: attr(),
        /**
         * Determines the function to execute when this suggestion list should
         * be closed. The function is called with no parameter.
         */
        onSuggestionListClosed: attr(),
        /**
         * Determines the function to execute when a suggestion is selected.
         * The function is called with one parameter, which is the record that
         * was selected.
         */
        onSuggestionSelected: attr(),
        /**
         * Determines the target model name of this suggestion list.
         */
        suggestionModelName: attr({
            required: true,
        }),
        /**
         * Determines the search term to use for suggestions.
         */
        suggestionSearchTerm: attr({
            default: '',
            required: true,
        }),
        /**
         * Determines in regard to which thread (if any) this suggestion list
         * should return values. Useful to prioritize and/or restrict results in
         * the context of a given thread
         */
        thread: many2one('mail.thread'),
    };

    SuggestionList.modelName = 'mail.suggestion_list';

    return SuggestionList;
}

registerNewModel('mail.suggestion_list', factory);
