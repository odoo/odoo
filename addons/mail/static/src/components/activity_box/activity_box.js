/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ActivityBoxView extends Component {

    /**
     * @returns {ActivityBoxView}
     */
    get activityBoxView() {
        return this.props.record;
    }

}

Object.assign(ActivityBoxView, {
    props: { record: Object },
    template: 'mail.ActivityBoxView',
});

registerMessagingComponent(ActivityBoxView);
