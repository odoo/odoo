/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiCategoryView',
    identifyingFields: ['emojiCategoryBarViewOwner', 'emojiCategory'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClick() {
            if (!this.emojiSubgridView.component.root.el) {
                return;
            }
            this.emojiSubgridView.component.root.el.scrollIntoView();
            this.emojiCategoryBarViewOwner.emojiPickerViewOwner.emojiSearchBar.reset();
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
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
        }),
        emojiCategoryBarViewOwner: one('EmojiCategoryBarView', {
            inverse: 'emojiCategoryViews',
            readonly: true,
            required: true,
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
