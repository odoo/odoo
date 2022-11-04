/** @odoo-module **/

import { attr, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiGridLoadingScreen',
    template: 'mail.EmojiGridLoadingScreen',
    templateGetter: 'EmojiGridLoadingScreen',
    fields: {
        emojiGridViewOwner: one('EmojiGridView', { identifying: true, inverse: 'loadingScreenView' }),
        text: attr({
            compute() {
                return this.env._t("Loading...");
            },
        }),
    },
});
