/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategoryView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick() {
            this.emojiPickerView.emojiSearchBarView.reset();
            let categoryRowScrollPosition = Math.max(
                0,
                // Index of the beginning of the category
                (this.emojiPickerView.emojiGridView.rowHeight * this.viewCategory.emojiGridRowView.index)
                -
                // Cancels the amount of buffer rows
                (this.emojiPickerView.emojiGridView.rowHeight * this.emojiPickerView.emojiGridView.topBufferAmount)
            );
            this.emojiPickerView.emojiGridView.containerRef.el.scrollTo({ top: categoryRowScrollPosition });
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
        emojiPickerView: one('EmojiPickerView', {
            related: 'emojiCategoryBarViewOwner.emojiPickerView',
        }),
        isActive: attr({
            compute() {
                return Boolean(this.viewCategory.emojiPickerViewAsActive);
            },
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
