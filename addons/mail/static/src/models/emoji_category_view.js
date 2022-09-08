/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiCategoryView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick() {
            this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiSearchBarView.reset();
            let categoryRowScrollPosition = Math.max(
                0,
                // Index of the beginning of the category
                (this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.rowHeight * this.viewCategory.emojiGridRowView.index)
                -
                // Cancels the amount of buffer rows
                (this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.rowHeight * this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.topBufferAmount)
            );
            this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.containerRef.el.scrollTo({ top: categoryRowScrollPosition });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseenter(ev) {
            this.update({ isHovered: true });
        },
        /**
         * @param {MouseEvent} ev
         */
        onMouseleave(ev) {
            this.update({ isHovered: false });
        },
    },
    fields: {
        category: one('EmojiCategory', {
            related: 'viewCategory.category',
        }),
        emojiCategoryBarViewOwner: one('EmojiCategoryBarView', {
            identifying: true,
            inverse: 'emojiCategoryViews',
        }),
        isActive: attr({
            compute() {
                return Boolean(this.viewCategory.emojiPickerViewAsActive);
            },
        }),
        isDisabled: attr({
            compute() {
                if (!this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiSearchBarView) {
                    return clear();
                }
                return Boolean(this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiSearchBarView.currentSearch !== "");
            },
            default: false,
        }),
        isHovered: attr({
            default: false,
        }),
        viewCategory: one('EmojiPickerView.Category', {
            identifying: true,
            inverse: 'emojiCategoryView',
        }),
    }
});
