/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiPicker extends Component {}

Object.assign(EmojiPicker, {
    props: { record: Object },
    template: 'mail.EmojiPicker',
});

registerMessagingComponent(EmojiPicker);
