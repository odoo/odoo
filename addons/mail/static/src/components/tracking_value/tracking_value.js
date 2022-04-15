/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class TrackingValue extends Component {

    /**
     * @returns {TrackingValue}
     */
    get trackingValue() {
        return this.props.value;
    }

}

Object.assign(TrackingValue, {
    props: { value: Object },
    template: 'mail.TrackingValue',
});

registerMessagingComponent(TrackingValue);
