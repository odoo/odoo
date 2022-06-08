/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { insertAndReplace, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'EmojiListView',
    identifyingFields: ['popoverViewOwner'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickEmoji(ev) {
            if (this.popoverViewOwner.messageActionListOwnerAsReaction) {
                this.popoverViewOwner.messageActionListOwnerAsReaction.onClickReaction(ev);
            } else if (this.popoverViewOwner.composerViewOwnerAsEmoji) {
                this.popoverViewOwner.composerViewOwnerAsEmoji.onClickEmoji(ev);
            }
        },
        
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiViews() {
            return insertAndReplace(
                this.messaging.emojiRegistry.allEmojis.map(emoji => {
                    return { emoji: replace(emoji) };
                })
            );
        },
        
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeEmojiCategoryViews() {
            return insertAndReplace(
                this.messaging.emojiRegistry.allCategories.map(emojiCategory => {
                    return { emojiCategory: replace(emojiCategory) };
                })
            );
        },
    },
    fields: {
        emojiCategoryViews: many('EmojiCategoryView', {
            compute: '_computeEmojiCategoryViews',
            inverse: 'emojiListView',
            readonly: true,
            isCausal: true,
        }),
        emojiViews: many('EmojiView', {
            compute: '_computeEmojiViews',
            inverse: 'emojiListView',
            readonly: true,
            isCausal: true,
        }),
        popoverViewOwner: one('PopoverView', {
            inverse: 'emojiListView',
            readonly: true,
            required: true,
        }),
    },
});
