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
            this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiSearchBarView.reset();
            let categoryRowScrollPosition = this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.rowHeight * this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiCategoryRowIndexes.get(this.emojiCategory)[0]; //Index of the beginning of the category
            categoryRowScrollPosition -= this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.topBufferAmount * this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.rowHeight; //Cancels the amount of buffer rows
            if (categoryRowScrollPosition < 0) {
                categoryRowScrollPosition = 0;
            }
            this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiGridView.containerRef.el.scrollTo(0, categoryRowScrollPosition);
        },
        setAsActiveCategory() {
            this.update({ emojiCategoryBarViewOwnerAsActiveByUser: this.emojiCategoryBarViewOwner });
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
        emojiCategory: one('EmojiCategory', {
            identifying: true,
            inverse: 'emojiCategoryViews',
        }),
        emojiCategoryBarViewOwner: one('EmojiCategoryBarView', {
            identifying: true,
            inverse: 'emojiCategoryViews',
        }),
        emojiCategoryBarViewOwnerAsActiveByUser: one('EmojiCategoryBarView', {
            inverse: 'activeByUserCategoryView',
        }),
        emojiCategoryBarViewOwnerAsActive: one('EmojiCategoryBarView', {
            inverse: 'activeCategoryView',
        }),
        isHovered: attr({
            default: false,
        }),
    }
});
