/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class Activity extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {ActivityView}
     */
    get activityView() {
        return this.messaging && this.messaging.models['ActivityView'].get(this.props.activityViewLocalId);
    }

}

Object.assign(Activity, {
    props: {
        activityViewLocalId: String,
    },
    template: 'mail.Activity',
});

registerMessagingComponent(Activity);
