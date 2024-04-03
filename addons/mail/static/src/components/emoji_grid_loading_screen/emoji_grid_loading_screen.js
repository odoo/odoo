/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class EmojiGridLoadingScreen extends Component {
    /**
     * @returns {EmojiGridLoadingScreen}
     */
    get EmojiGridLoadingScreen() {
        return this.props.record;
    }
}

Object.assign(EmojiGridLoadingScreen, {
    props: { record: Object },
    template: 'mail.EmojiGridLoadingScreen',
});

registerMessagingComponent(EmojiGridLoadingScreen);
