/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiGridRowView extends Component {
    /**
     * @returns {EmojiGridRowView}
     */
    get emojiGridRowView() {
        return this.props.record;
    }
}

Object.assign(EmojiGridRowView, {
    props: { record: Object },
    template: 'mail.EmojiGridRowView',
});

registerMessagingComponent(EmojiGridRowView);
