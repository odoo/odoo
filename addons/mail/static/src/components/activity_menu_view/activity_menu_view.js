/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class ActivityMenuView extends Component {
    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }
    /**
     * @returns {ActivityMenuView}
     */
    get activityMenuView() {
        return this.props.record;
    }
}

Object.assign(ActivityMenuView, {
    props: { record: Object },
    template: 'mail.ActivityMenuView',
});

registerMessagingComponent(ActivityMenuView);
