/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

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
