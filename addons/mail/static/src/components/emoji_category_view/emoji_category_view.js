/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiCategoryView extends Component {
    /**
     * @returns {EmojiCategoryView}
     */
    get emojiCategoryView() {
        return this.props.record;
    }
}

Object.assign(EmojiCategoryView, {
    props: { record: Object },
    template: 'mail.EmojiCategoryView',
});

registerMessagingComponent(EmojiCategoryView);
