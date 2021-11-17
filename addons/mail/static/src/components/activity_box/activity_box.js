/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityBox extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Chatter}
     */
    get activityBoxView() {
        return this.messaging.models['mail.activity_box_view'].get(this.props.activityBoxViewLocalId);
    }

}

Object.assign(ActivityBox, {
    props: {
        activityBoxViewLocalId: String,
    },
    template: 'mail.ActivityBox',
});

registerMessagingComponent(ActivityBox);
