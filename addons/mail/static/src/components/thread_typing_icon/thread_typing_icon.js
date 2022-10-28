/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ThreadTypingIcon extends Component {

    /**
     * @returns {ThreadTypingIconView}
     */
    get threadTypingIconView() {
        return this.props.record;
    }

}

Object.assign(ThreadTypingIcon, {
    props: { record: Object },
    template: 'mail.ThreadTypingIcon',
});

registerMessagingComponent(ThreadTypingIcon);
