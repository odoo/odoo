/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, increment } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiGridView',
    recordMethods: {
        calculateDimensions() {
            if (!this.containerRef.el || !this.viewBlockRef.el) {
                return;
            }
            const fittingAmount = this.containerRef.el.clientHeight / this.rowHeight;
            const amountToDisplay = fittingAmount + this.additionalRowsToRender;
            this.update({
                amountToDisplay,
                scrollRecomputeCount: increment()
            });
        },
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
                const rowIndex = this.firstRenderedRowIndex;
                if (
                    viewCategory.emojiGridRowView &&
                    rowIndex >= viewCategory.emojiGridRowView.index &&
                    (viewCategory.emojiPickerViewOwnerAsLastCategory || rowIndex <= viewCategory.endSectionIndex)
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
        additionalRowsToRender: attr({
            default: 4,
        }),
        amountOfItemsPerRow: attr({
            default: 9,
        }),
        amountToDisplay: attr({
            default: 50,
        }),
        categorySelectedByUser: one('EmojiPickerView.Category'),
        containerRef: attr(),
        distanceFromTop: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                if (!this.listRef || !this.listRef.el) {
                    return clear();
                }
                return this.scrollPercentage * this.listRef.el.clientHeight;
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
        firstRenderedRowIndex: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                let value;
                if (this.scrollIndex - this.amountToDisplay >= this.rows.length) {
                    value = this.scrollIndex - this.amountToDisplay;
                } else {
                    value = this.scrollIndex;
                }
                return Math.floor(value);
            },
            default: 0,
        }),
        height: attr({
            default: "275px",
        }),
        itemWidth: attr({
            default: 30,
        }),
        lastRenderedRowIndex: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                let value;
                if (this.firstRenderedRowIndex + this.amountToDisplay >= this.rows.length) {
                    value = Math.max(this.rows.length - 1, 0);
                } else {
                    value = this.firstRenderedRowIndex + this.amountToDisplay;
                }
                return Math.floor(value);
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
        scrollIndex: attr({
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                return (this.scrollPercentage * this.rows.length);
            },
            default: 0,
        }),
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
        width: attr({
            compute() {
                return `${this.itemWidth * this.amountOfItemsPerRow + this.scrollbarThresholdWidth}px`;
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
