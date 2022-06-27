/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiCategory extends Component {}

Object.assign(EmojiCategory, {
    props: {
        emojiCategoryView: Object,
    },
    template: 'mail.EmojiCategory',
});

registerMessagingComponent(EmojiCategory);
