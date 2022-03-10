/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, decrement, increment, insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'AutocompleteInputSuggestionView',
    identifyingFields: ['popoverViewOwner'],
    recordMethods: {
        changeActiveFirst() {
            this.update({ activeIndex: 0 });
        },
        changeActiveLast() {
            this.update({ activeIndex: this.itemViews.length - 1 });
        },
        changeActiveNext() {
            if (this.activeIndex === this.itemViews.length - 1) {
                this.changeActiveFirst();
            } else {
                this.update({ activeIndex: increment() });
            }
        },
        changeActivePrevious() {
            if (this.activeIndex === 0) {
                this.changeActiveLast();
            } else {
                this.update({ activeIndex: decrement() });
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeActiveItemView() {
            if (this.itemViews.length === 0) {
                return clear();
            }
            if (this.activeIndex > this.itemViews.length - 1) {
                return replace(this.itemViews[this.itemViews.length - 1]);
            }
            return replace(this.itemViews[this.activeIndex]);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeItemViews() {
            if (this.suggestedPartners.length === 0) {
                return clear();
            }
            return insertAndReplace(this.suggestedPartners.map(partner => ({ suggestedPartner: replace(partner) })));
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeSuggestedPartners() {
            if (this.popoverViewOwner.autocompleteInputViewOwner) {
                return replace(this.popoverViewOwner.autocompleteInputViewOwner.suggestedPartners);
            }
            return clear();
        },
        /**
         * @private
         * @returns {integer|FieldCommand}
         */
        _computeWidth() {
            if (this.popoverViewOwner.autocompleteInputViewOwner && this.popoverViewOwner.autocompleteInputViewOwner.width !== undefined) {
                return this.popoverViewOwner.autocompleteInputViewOwner.width - 2; // compensation of 2px due to 1px border
            }
            return clear();
        },
    },
    fields: {
        activeIndex: attr({
            default: 0,
        }),
        activeItemView: one('AutocompleteInputSuggestionItemView', {
            inverse: 'autocompleteInputSuggestionViewOwnerAsActive',
            compute: '_computeActiveItemView',
        }),
        itemViews: many('AutocompleteInputSuggestionItemView', {
            compute: '_computeItemViews',
            inverse: 'autocompleteInputSuggestionViewOwner',
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            inverse: 'autocompleteInputSuggestionView',
            readonly: true,
            required: true,
        }),
        suggestedPartners: many('Partner', {
            compute: '_computeSuggestedPartners',
        }),
        width: attr({
            compute: '_computeWidth',
            default: undefined,
        }),
    },
});
