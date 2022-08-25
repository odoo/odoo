/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Emoji extends Component {
    /**
     * @returns {EmojiView}
     */
    get emojiView() {
        return this.props.record;
    }
}

Object.assign(Emoji, {
    props: { record: Object },
    template: 'mail.Emoji',
});

registerMessagingComponent(Emoji);
