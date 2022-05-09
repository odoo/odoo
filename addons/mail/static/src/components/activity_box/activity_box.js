/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityBox extends Component {

    /**
     * @returns {ActivityBoxView}
     */
    get activityBoxView() {
        return this.props.record;
    }

}

Object.assign(ActivityBox, {
    props: { record: Object },
    template: 'mail.ActivityBox',
});

registerMessagingComponent(ActivityBox);
