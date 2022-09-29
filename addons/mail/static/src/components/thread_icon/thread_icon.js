/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ThreadIcon extends Component {

    /**
     * @returns {ThreadIconView}
     */
     get threadIconView() {
        return this.props.record;
    }

}

Object.assign(ThreadIcon, {
    props: { record: Object },
    template: 'mail.ThreadIcon',
});

registerMessagingComponent(ThreadIcon);
