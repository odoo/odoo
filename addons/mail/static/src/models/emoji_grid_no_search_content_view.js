/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiGridNoSearchContentView',
    fields: {
        emojiGridViewOwner: one('EmojiGridView', {
            identifying: true,
            inverse: 'searchNoContentView',
        }),
        text: attr({
            compute() {
                return this.env._t("No emoji match your search");
            },
        }),
    },
});
