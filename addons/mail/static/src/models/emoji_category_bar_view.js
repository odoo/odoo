/** @odoo-module **/

import { clear, many, one, registerModel } from '@mail/model';

registerModel({
    name: 'EmojiCategoryBarView',
    template: 'mail.EmojiCategoryBarView',
    templateGetter: 'emojiCategoryBarView',
    fields: {
        emojiCategoryViews: many('EmojiCategoryView', { inverse: 'emojiCategoryBarViewOwner',
            compute() {
                if (!this.emojiPickerView) {
                    return clear();
                }
                return this.emojiPickerView.categories.map(category => ({ viewCategory: category }));
            },
        }),
        emojiPickerHeaderViewOwner: one('EmojiPickerHeaderView', { identifying: true, inverse: 'emojiCategoryBarView' }),
        emojiPickerView: one('EmojiPickerView', { related: 'emojiPickerHeaderViewOwner.emojiPickerViewOwner' }),
    },
});
