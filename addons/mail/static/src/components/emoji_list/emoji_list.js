/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiList extends Component {}

Object.assign(EmojiList, {
    props: {
        emojiList: Object,
    },
    template: 'mail.EmojiList',
});

registerMessagingComponent(EmojiList);
