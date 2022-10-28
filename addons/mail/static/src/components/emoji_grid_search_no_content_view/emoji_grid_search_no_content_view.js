/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class EmojiGridSearchNoContentView extends Component {
    /**
     * @returns {EmojiGridSearchNoContentView}
     */
    get emojiGridSearchNoContentView() {
        return this.props.record;
    }
}

Object.assign(EmojiGridSearchNoContentView, {
    props: { record: Object },
    template: 'mail.EmojiGridSearchNoContentView',
});

registerMessagingComponent(EmojiGridSearchNoContentView);
