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
            this.emojiPickerView.emojiGridView.update({ categorySelectedByUser: this.viewCategory });
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
