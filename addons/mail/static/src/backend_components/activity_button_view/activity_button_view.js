/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class ActivityButtonView extends Component {

    setup() {
        super.setup();
        useRefToModel({ fieldName: 'buttonRef', refName: 'button' });
    }

    get activityButtonView() {
        return this.props.record;
    }

}

Object.assign(ActivityButtonView, {
    props: { record: Object },
    template: 'mail.ActivityButtonView',
});

registerMessagingComponent(ActivityButtonView);
