/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'EmojiGridLoadingScreen',
    fields: {
        emojiGridViewOwner: one('EmojiGridView', {
            identifying: true,
            inverse: 'loadingScreenView',
        }),
        text: attr({
            compute() {
                return this.env._t("Loading...");
            },
        }),
    },
});
