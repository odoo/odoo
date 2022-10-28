/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";

import { Component } from '@odoo/owl';

export class ActivityView extends Component {

    /**
     * @override
     */
     setup() {
        super.setup();
        useRefToModel({ fieldName: 'markDoneButtonRef', refName: 'markDoneButton', });
    }

    /**
     * @returns {ActivityView}
     */
    get activityView() {
        return this.props.record;
    }

}

Object.assign(ActivityView, {
    props: { record: Object },
    template: 'mail.ActivityView',
    components: { Popover },
});

registerMessagingComponent(ActivityView);
