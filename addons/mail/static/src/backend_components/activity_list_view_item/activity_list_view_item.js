/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityListViewItem extends Component {

    get activityListViewItem() {
        return this.props.record;
    }

}

Object.assign(ActivityListViewItem, {
    props: { record: Object },
    template: 'mail.ActivityListViewItem',
});

registerMessagingComponent(ActivityListViewItem);
