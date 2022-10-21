/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one, many } from '@mail/model/model_field';

registerModel({
    name: 'MessageContextMostUsedImojiView',
    lifecycleHooks: {
        _created() {
            if (this.messaging.emojiRegistry.isLoaded || this.messaging.emojiRegistry.isLoading) {
                return;
            }
            this.messaging.emojiRegistry.loadEmojiData();
        },
    },
    fields: {
        allEmojis: many('Emoji', {
            inverse: 'emojiMostUsed',
        }),
        MostUsedImojiViewOwner: one('MessageContextHeaderView', {
            identifying: true,
            inverse: 'mostEmojiUsedItems',
        }),
    },
});
