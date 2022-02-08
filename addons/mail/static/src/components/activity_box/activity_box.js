/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityBox extends Component {

    /**
     * @returns {ActivityBoxView}
     */
    get activityBoxView() {
        return this.messaging && this.messaging.models['ActivityBoxView'].get(this.props.localId);
    }

}

Object.assign(ActivityBox, {
    props: { localId: String },
    template: 'mail.ActivityBox',
});

registerMessagingComponent(ActivityBox);
