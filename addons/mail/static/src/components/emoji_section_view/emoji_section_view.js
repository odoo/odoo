/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiSectionView extends Component {
    /**
     * @returns {EmojiSectionView}
     */
    get emojiSectionView() {
        return this.props.record;
    }
}

Object.assign(EmojiSectionView, {
    props: { record: Object },
    template: 'mail.EmojiSectionView',
});

registerMessagingComponent(EmojiSectionView);
