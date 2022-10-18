/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component, onMounted } = owl;

export class ActivityMarkDonePopoverContent extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'feedbackTextareaRef', refName: 'feedbackTextarea' });
        onMounted(this.activityMarkDonePopoverContentView.onMounted);
    }

    /**
     * @returns {ActivityMarkDonePopoverContentView}
     */
    get activityMarkDonePopoverContentView() {
        return this.props.record;
    }

}

Object.assign(ActivityMarkDonePopoverContent, {
    props: { record: Object },
    template: 'mail.ActivityMarkDonePopoverContent',
});

registerMessagingComponent(ActivityMarkDonePopoverContent);
