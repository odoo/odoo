/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";

const { Component } = owl;

export class Activity extends Component {

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

Object.assign(Activity, {
    props: { record: Object },
    template: 'mail.Activity',
    components: { Popover },
});

registerMessagingComponent(Activity);
