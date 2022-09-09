/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityListViewItem extends Component {

    setup() {
        super.setup();
        useRefToModel({ fieldName: 'markDoneButtonRef', refName: 'markDoneButton' });
    }
    get activityListViewItem() {
        return this.props.record;
    }

}

Object.assign(ActivityListViewItem, {
    props: { record: Object },
    template: 'mail.ActivityListViewItem',
});

registerMessagingComponent(ActivityListViewItem);
