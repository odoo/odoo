/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityListView extends Component {

    get activityListView() {
        return this.props.record;
    }

}

Object.assign(ActivityListView, {
    props: { record: Object },
    template: 'mail.ActivityListView',
});

registerMessagingComponent(ActivityListView);
