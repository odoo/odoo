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
