/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class EmojiPickerHeaderActionListView extends Component {

    /**
     * @returns {EmojiPickerHeaderActionListView}
     */
    get emojiPickerHeaderActionListView() {
        return this.props.record;
    }

}

Object.assign(EmojiPickerHeaderActionListView, {
    props: { record: Object },
    template: 'mail.EmojiPickerHeaderActionListView',
});

registerMessagingComponent(EmojiPickerHeaderActionListView);
