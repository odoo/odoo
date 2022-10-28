/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class EmojiGridSectionView extends Component {
    /**
     * @returns {EmojiGridSectionView}
     */
    get emojiGridSectionView() {
        return this.props.record;
    }
}

Object.assign(EmojiGridSectionView, {
    props: { record: Object },
    template: 'mail.EmojiGridSectionView',
});

registerMessagingComponent(EmojiGridSectionView);
