/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiGridView extends Component {
    /**
     * @returns {EmojiGridView}
     */
    get emojiGridView() {
        return this.props.record;
    }
}

Object.assign(EmojiGridView, {
    props: { record: Object },
    template: 'mail.EmojiGridView',
});

registerMessagingComponent(EmojiGridView);
