/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiListView',
    identifyingFields: ['popoverViewOwner'],
    lifecycleHooks: {
        _created() {
            this.onClickEmoji = this.onClickEmoji.bind(this);
        },
    },
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
    },
    fields: {
        popoverViewOwner: one2one('PopoverView', {
            inverse: 'emojiListView',
            readonly: true,
            required: true,
        }),
    },
});
