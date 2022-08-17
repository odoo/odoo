/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiPickerView extends Component {
    setup() {


    }
    /**
     * @returns {EmojiPickerView}
     */
    get emojiPickerView() {
        return this.props.record;
    }
}

Object.assign(EmojiPickerView, {
    props: { record: Object },
    template: 'mail.EmojiPickerView',
});

registerMessagingComponent(EmojiPickerView);
