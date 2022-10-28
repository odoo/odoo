/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class EmojiGridItemView extends Component {
    /**
     * @returns {EmojiGridItemView}
     */
    get emojiGridItemView() {
        return this.props.record;
    }
}

Object.assign(EmojiGridItemView, {
    props: { record: Object },
    template: 'mail.EmojiGridItemView',
});

registerMessagingComponent(EmojiGridItemView);
