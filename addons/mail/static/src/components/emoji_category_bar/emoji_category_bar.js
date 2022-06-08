/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiCategoryBar extends Component {}

Object.assign(EmojiCategoryBar, {
    props: {
        emojiCategoryBar: Object,
    },
    template: 'mail.EmojiCategoryBar',
});

registerMessagingComponent(EmojiCategoryBar);
