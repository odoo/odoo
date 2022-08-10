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
            this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiSearchBar.reset();
            if (!this.emojiSubgridView.categoryNameRef.el) {
                return;
            }
            this.emojiSubgridView.categoryNameRef.el.scrollIntoView();
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
        emojiSubgridView: one('EmojiSubgridView', {
            inverse: "emojiCategoryView",
            isCausal: true,
        }),
        isHovered: attr({
            default: false,
        }),
    }
});
