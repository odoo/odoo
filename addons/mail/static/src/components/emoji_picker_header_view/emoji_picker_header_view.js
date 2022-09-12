/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiPickerHeaderView extends Component {

    /**
     * @returns {EmojiPickerHeaderView}
     */
    get emojiPickerHeaderView() {
        return this.props.record;
    }

}

Object.assign(EmojiPickerHeaderView, {
    props: { record: Object },
    template: 'mail.EmojiPickerHeaderView',
});

registerMessagingComponent(EmojiPickerHeaderView);
