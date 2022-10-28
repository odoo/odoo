/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class EmojiCategoryBarView extends Component {
    /**
     * @returns {EmojiCategoryBarView}
     */
    get emojiCategoryBarView() {
        return this.props.record;
    }
}

Object.assign(EmojiCategoryBarView, {
    props: { record: Object },
    template: 'mail.EmojiCategoryBarView',
});

registerMessagingComponent(EmojiCategoryBarView);
