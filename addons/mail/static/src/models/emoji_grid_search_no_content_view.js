/** @odoo-module **/

import { attr, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiGridSearchNoContentView',
    template: 'mail.EmojiGridSearchNoContentView',
    templateGetter: 'emojiGridSearchNoContentView',
    fields: {
        emojiGridViewOwner: one('EmojiGridView', { identifying: true, inverse: 'searchNoContentView' }),
        text: attr({
            compute() {
                return this.env._t("No emoji match your search");
            },
        }),
    },
});
