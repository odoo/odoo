/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class EmojiView extends Component {
    /**
     * @returns {EmojiView}
     */
    get emojiView() {
        return this.props.record;
    }
}

Object.assign(EmojiView, {
    props: { record: Object },
    template: 'mail.EmojiView',
});

registerMessagingComponent(EmojiView);
