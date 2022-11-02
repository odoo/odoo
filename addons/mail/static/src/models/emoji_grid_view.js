/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { attr, clear, increment, many, one, Model } from '@mail/model';

Model({
    name: 'EmojiGridView',
    template: 'mail.EmojiGridView',
    componentSetup() {
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    },
    lifecycleHooks: {
        _created() {
            browser.addEventListener('keydown', this._onKeyDown);
        },
        async _willDelete() {
            browser.removeEventListener('keydown', this._onKeyDown);
        },
    },
    recordMethods: {
        adjustScroll() {
            if (!this.selectedEmojiView) {
                return;
            }
            const index = this.selectedEmojiView.emojiGridRowViewOwner.index;
            if (this.scrollIndex <= index && index < this.scrollIndex + Math.floor(this.visibleMaxAmount)) {
                return;
            }
            this.containerRef.el.scrollTo({
                top: this.rowHeight * index,
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
                this.emojiPickerViewOwner.currentSearch === ""
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
        _getNextEmojiRow() {
            if (this.rows.length === this.selectedEmojiView.emojiGridRowViewOwner.index + 1) {
                return this.selectedEmojiView.emojiGridRowViewOwner;
            } else {
                for (let i = this.selectedEmojiView.emojiGridRowViewOwner.index + 1; i < this.rows.length; i++) {
                    const row = this.rows[i];
                    if (row.items.length) {
                        return row;
                    }
                }
                return this.selectedEmojiView.emojiGridRowViewOwner;
            }
        },
        _getPreviousEmojiRow() {
            if (this.selectedEmojiView.emojiGridRowViewOwner.index === 0) {
                return this.selectedEmojiView.emojiGridRowViewOwner;
            }
            for (let i = this.selectedEmojiView.emojiGridRowViewOwner.index - 1; i >= 0; i--) {
                const row = this.rows[i];
                if (row.items.length) {
                    return row;
                }
            }
            return this.selectedEmojiView.emojiGridRowViewOwner;
        },
        _onArrowDown() {
            if (!this.rows.length > this.selectedEmojiView.emojiGridRowViewOwner.index + 1) {
                return;
            }
            const targetRow = this._getNextEmojiRow();
            const targetIndex = Math.min(this.selectedEmojiView.index, targetRow.items.length - 1);
            this.update({ lastSelectedEmojiView: targetRow.items[targetIndex] });
        },
        _onArrowLeft() {
            if (this.selectedEmojiView.index === 0) {
                if (this.selectedEmojiView.emojiGridRowViewOwner.index === 0) {
                    return;
                } else {
                    const targetRow = this._getPreviousEmojiRow();
                    this.update({ lastSelectedEmojiView: targetRow.items[targetRow.items.length - 1] });
                }
            } else {
                const emojiView = this.selectedEmojiView.emojiGridRowViewOwner.items[this.selectedEmojiView.index - 1];
                this.update({ lastSelectedEmojiView: emojiView });
            }
        },
        _onArrowRight() {
            if (this.selectedEmojiView.index === this.selectedEmojiView.emojiGridRowViewOwner.items.length - 1) {
                if (this.selectedEmojiView.emojiGridRowViewOwner.index === this.rows.length - 1) {
                    return;
                } else {
                    const targetRow = this._getNextEmojiRow();
                    this.update({ lastSelectedEmojiView: targetRow.items[0] });
                }
            } else {
                const emojiView = this.selectedEmojiView.emojiGridRowViewOwner.items[this.selectedEmojiView.index + 1];
                this.update({ lastSelectedEmojiView: emojiView });
            }
        },
        _onArrowUp() {
            if (this.selectedEmojiView.emojiGridRowViewOwner.index === 0) {
                return;
            } else {
                const targetRow = this._getPreviousEmojiRow();
                const targetIndex = Math.min(this.selectedEmojiView.index, targetRow.items.length - 1);
                this.update({ lastSelectedEmojiView: targetRow.items[targetIndex] });
            }
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
        _onEnter() {
            if (this.selectedEmojiView) {
                this.selectedEmojiView.sendEmoji();
            }
        },
        _onKeyDown(ev) {
            switch (ev.key) {
                case 'Enter':
                    this._onEnter();
                    return;
                case 'ArrowDown':
                    this._onArrowDown();
                    break;
                case 'ArrowUp':
                    this._onArrowUp();
                    break;
                case 'ArrowLeft':
                    this._onArrowLeft();
                    break;
                case 'ArrowRight':
                    this._onArrowRight();
                    break;
            }
            this.adjustScroll();
        },
        /**
         * @private
         * @returns {boolean}
         * Filters emoji according to the current search terms.
         */
        _filterEmoji(emoji) {
            return (emoji._isStringInEmojiKeywords(this.emojiPickerViewOwner.currentSearch));
        },
    },
    fields: {
        amountOfItemsPerRow: attr({ default: 9 }),
        categorySelectedByUser: one('EmojiPickerView.Category'),
        containerRef: attr({ ref: 'containerRef' }),
        /**
         * Distance of the rendered rows from top.
         * This is from the PoV of 1st rendered row, including extra rendered rows!
         */
        distanceFromTop: attr({ default: 0,
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
        }),
        distanceInRowOffset: attr({ default: 0,
            compute() {
                return this.distanceFromTop % this.rowHeight;
            },
        }),
        emojiPickerViewOwner: one('EmojiPickerView', { identifying: true, inverse: 'emojiGridView' }),
        /**
         * Extra rows above and below the visible part.
         * 10 means 10 rows above and 10 rows below.
         */
        extraRenderRowsAmount: attr({ default: 10 }),
        firstRenderedRowIndex: attr({ default: 0,
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                return Math.max(
                    this.scrollIndex - this.extraRenderRowsAmount,
                    0,
                );
            },
        }),
        hasNoSearchResult: attr({
            compute() {
                if (this.emojiPickerViewOwner.currentSearch !== "" && this.rows.length === 0) {
                    return true;
                }
                return clear();
            },
            default: false,
        }),
        height: attr({
            compute() {
                return this.rowHeight * this.visibleMaxAmount;
            },
        }),
        /**
         * EmojiView selected through arrow navigation or hover
         */
        lastSelectedEmojiView: one('EmojiView', { inverse: 'emojiGridViewAsLastSelected' }),
        /**
         * lastSelectedEmojiView if valid, else the first rendered available
         */
        selectedEmojiView: one('EmojiView', {
            inverse: 'emojiGridViewAsSelected',
            compute() {
                if (this.lastSelectedEmojiView) {
                    return this.lastSelectedEmojiView;
                }
                if (this.rows && this.scrollIndex !== undefined) {
                    for (let i = this.scrollIndex; i < this.rows.length; i++) {
                        const row = this.rows[i];
                        if (row.items.length) {
                            return row.items[0];
                        }
                    }

                }
            }
        }),
        itemWidth: attr({ default: 30 }),
        lastRenderedRowIndex: attr({ default: 0,
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
        }),
        listHeight: attr({ default: 0,
            compute() {
                return this.rowHeight * this.rows.length;
            },
        }),
        listRef: attr({ ref: 'listRef' }),
        loadingText: attr({
            compute() {
                return this.env._t("Loading...");
            },
        }),
        nonSearchRowRegistry: one('EmojiGridViewRowRegistry', { default: {}, inverse: 'emojiGridViewOwnerAsNonSearch' }),
        noSearchResultText: attr({
            compute() {
                return this.env._t("No emoji match your search");
            },
        }),
        onScrollThrottle: one('Throttle', { inverse: 'emojiGridViewAsOnScroll',
            compute() {
                return { func: () => this.update({ scrollRecomputeCount: increment() }) };
            },
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
        rowHeight: attr({ default: 30 }),
        rows: many('EmojiGridRowView', {
            compute() {
                if (this.emojiPickerViewOwner.currentSearch !== "") {
                    return this.searchRowRegistry.rows;
                }
                return this.nonSearchRowRegistry.rows;
            },
        }),
        /**
         * Scroll index of the 1st visible rendered rows (so excluding the extra rendered rendered rows).
         */
        scrollIndex: attr({ default: 0,
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                return Math.floor(this.scrollPercentage * this.rows.length);
            },
        }),
        /**
         * Scroll percentage of the 1st visible rendered rows.
         */
        scrollPercentage: attr({ default: 0,
            compute() {
                this.scrollRecomputeCount; // observe scroll changes
                if (!this.containerRef || !this.containerRef.el) {
                    return clear();
                }
                return this.containerRef.el.scrollTop / this.containerRef.el.scrollHeight;
            },
        }),
        scrollbarThresholdWidth: attr({ default: 15 }),
        scrollRecomputeCount: attr({ default: 0 }),
        searchRowRegistry: one('EmojiGridViewRowRegistry', { default: {}, inverse: 'emojiGridViewOwnerAsSearch' }),
        viewBlockRef: attr({ ref: 'viewBlockRef' }),
        /**
         * Amount of emoji that are visibly rendered in emoji grid.
         * Decimal determines the partial visibility of the last emoji.
         * For example, 9.5 means 9 emojis fully visible, and the last is half visible.
         */
        visibleMaxAmount: attr({ default: 9.5 }),
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
