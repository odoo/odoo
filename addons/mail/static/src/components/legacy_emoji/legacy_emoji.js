/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class LegacyEmoji extends Component {}

Object.assign(LegacyEmoji, {
    props: {
        emojiView: Object,
    },
    template: 'mail.LegacyEmoji',
});

registerMessagingComponent(LegacyEmoji);
