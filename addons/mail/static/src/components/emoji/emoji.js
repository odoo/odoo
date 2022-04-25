/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Emoji extends Component {

    /**
     * @returns {EmojiListView}
     */
    get emojiListView() {
        return this.messaging && this.messaging.models['EmojiListView'].get(this.props.emojiListViewLocalId);
    }

}

Object.assign(Emoji, {
    props: {
        emoji: Object,
        emojiListViewLocalId: String,
    },
    template: 'mail.Emoji',
});

registerMessagingComponent(Emoji);
