/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Emoji extends Component {}

Object.assign(Emoji, {
    props: {
        emojiView: Object,
    },
    template: 'mail.Emoji',
});

registerMessagingComponent(Emoji);
