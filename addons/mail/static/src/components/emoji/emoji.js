/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Emoji extends Component {

    /**
     * @returns {EmojiListView}
     */
    get emojiListView() {
        return this.props.emojiListView;
    }

}

Object.assign(Emoji, {
    props: {
        emoji: Object,
        emojiListView: Object,
    },
    template: 'mail.Emoji',
});

registerMessagingComponent(Emoji);
