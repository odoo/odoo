/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, increment } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridView',
    recordMethods: {
        doJumpToCategorySelectedByUser() {
            this.containerRef.el.scrollTo({
                top: this.rowHeight * this.categorySelectedByUser.emojiGridRowView.index,
            });
            this.update({ categorySelectedByUser: clear() });
        },
        /**
         * Handles OWL update on component update.
         */
        onComponentUpdate() {
            if (
                this.categorySelectedByUser &&
                this.emojiPickerViewOwner.emojiSearchBarView.currentSearch === ""
            ) {
                this.doJumpToCategorySelectedByUser();
            }
        },
        onScroll() {
            if (!this.exists()) {
                return;
            }
            this.onScrollThrottle.do();
        },
        _onChangeScrollRecomputeCount() {
            for (const viewCategory of this.emojiPickerViewOwner.categories) {
                if (
                    viewCategory.emojiGridRowView &&
                    this.scrollIndex >= viewCategory.emojiGridRowView.index &&
                    (viewCategory.emojiPickerViewOwnerAsLastCategory || this.scrollIndex <= viewCategory.endSectionIndex)
                ) {
                    this.emojiPickerViewOwner.update({ activeCategoryByGridViewScroll: viewCategory });
                    break;
                }
            }
        },
        /**
         * @private
         * @returns {boolean}
         * Filters emoji according to the current search terms.
         */
        _filterEmoji(emoji) {
            return (emoji._isStringInEmojiKeywords(this.emojiPickerViewOwner.emojiSearchBarView.currentSearch));
        },
    },
    fields: {
        amountOfItemsPerRow: attr({
            default: 9,
        }),
        categorySelectedByUser: one('EmojiPickerView.Category'),
        containerRef: attr(),
        /**
         * Distance of the rendered rows from top.
         * This is from the PoV of 1st rendered row, including extra rendered rows!
         */
        distanceFromTop: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                if (!this.listRef || !this.listRef.el) {
                    return clear();
                }
                return Math.max(
                    (this.scrollPercentage * this.listRef.el.clientHeight - this.extraRenderRowsAmount * this.rowHeight),
                    0,
                );
            },
            default: 0,
        }),
        distanceInRowOffset: attr({
            compute() {
                return this.distanceFromTop % this.rowHeight;
            },
            default: 0,
        }),
        emojiPickerViewOwner: one('EmojiPickerView', {
            identifying: true,
            inverse: 'emojiGridView',
        }),
        /**
         * Extra rows above and below the visible part.
         * 10 means 10 rows above and 10 rows below.
         */
        extraRenderRowsAmount: attr({
            default: 10,
        }),
        firstRenderedRowIndex: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                return Math.max(
                    this.scrollIndex - this.extraRenderRowsAmount,
                    0,
                );
            },
            default: 0,
        }),
        height: attr({
            compute() {
                return this.rowHeight * 9.5;
            },
        }),
        hoveredEmojiView: one('EmojiView', {
            inverse: 'emojiGridViewAsHovered',
        }),
        itemWidth: attr({
            default: 30,
        }),
        lastRenderedRowIndex: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                let value;
                if (this.firstRenderedRowIndex + this.renderedMaxAmount >= this.rows.length) {
                    value = Math.max(this.rows.length - 1, 0);
                } else {
                    value = this.firstRenderedRowIndex + this.renderedMaxAmount;
                }
                return Math.ceil(value);
            },
            default: 0,
        }),
        listHeight: attr({
            compute() {
                return this.rowHeight * this.rows.length;
            },
            default: 0,
        }),
        listRef: attr(),
        nonSearchRowRegistry: one('EmojiGridViewRowRegistry', {
            default: {},
            inverse: 'emojiGridViewOwnerAsNonSearch',
        }),
        onScrollThrottle: one('Throttle', {
            compute() {
                return { func: () => this.update({ scrollRecomputeCount: increment() }) };
            },
            inverse: 'emojiGridViewAsOnScroll',
        }),
        renderedMaxAmount: attr({
            compute() {
                return this.extraRenderRowsAmount * 2 + Math.ceil(this.visibleMaxAmount);
            },
        }),
        renderedRows: many('EmojiGridRowView', {
            compute() {
                if (this.lastRenderedRowIndex + 1 - this.firstRenderedRowIndex < 0) {
                    return clear();
                }
                if (this.rows.length === 0) {
                    return clear();
                }
                return (
                    [...Array(this.lastRenderedRowIndex + 1 - this.firstRenderedRowIndex).keys()]
                    .map(relativeRowIndex => this.rows[this.firstRenderedRowIndex + relativeRowIndex])
                    .filter(row => row !== undefined) // some corner cases where very briefly it doesn't sync with rows and it's bigger
                );
            },
            sort: [['smaller-first', 'index']],
        }),
        rowHeight: attr({
            default: 30,
        }),
        rows: many('EmojiGridRowView', {
            compute() {
                if (this.emojiPickerViewOwner.emojiSearchBarView.currentSearch !== "") {
                    return this.searchRowRegistry.rows;
                }
                return this.nonSearchRowRegistry.rows;
            },
        }),
        /**
         * Scroll index of the 1st visible rendered rows (so excluding the extra rendered rendered rows).
         */
        scrollIndex: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                return Math.floor(this.scrollPercentage * this.rows.length);
            },
            default: 0,
        }),
        /**
         * Scroll percentage of the 1st visible rendered rows.
         */
        scrollPercentage: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                if (!this.containerRef || !this.containerRef.el) {
                    return clear();
                }
                return this.containerRef.el.scrollTop / this.containerRef.el.scrollHeight;
            },
            default: 0,
        }),
        scrollbarThresholdWidth: attr({
            default: 15,
        }),
        scrollRecomputeCount: attr({
            default: 0,
        }),
        searchNoContentView: one('EmojiGridNoSearchContentView', {
            compute() {
                if (this.emojiPickerViewOwner.emojiSearchBarView.currentSearch !== "" && this.rows.length === 0) {
                    return {};
                }
                return clear();
            },
            inverse: 'emojiGridViewOwner',
        }),
        searchRowRegistry: one('EmojiGridViewRowRegistry', {
            default: {},
            inverse: 'emojiGridViewOwnerAsSearch',
        }),
        viewBlockRef: attr(),
        /**
         * Amount of emoji that are visibly rendered in emoji grid.
         * Decimal determines the partial visibility of the last emoji.
         * For example, 9.5 means 9 emojis fully visible, and the last is half visible.
         */
        visibleMaxAmount: attr({
            default: 9.5,
        }),
        width: attr({
            compute() {
                return this.itemWidth * this.amountOfItemsPerRow + this.scrollbarThresholdWidth;
            },
        }),
    },
    onChanges: [
        {
            dependencies: ['scrollRecomputeCount'],
            methodName: '_onChangeScrollRecomputeCount',
        },
    ],
});
