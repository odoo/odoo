/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;
const { onMounted, useRef } = owl.hooks;

export class ActivityMarkDonePopover extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'ActivityMarkDonePopoverView', propNameAsRecordLocalId: 'localId' });
        useRefToModel({ fieldName: 'feedbackTextareaRef', modelName: 'ActivityMarkDonePopoverView', propNameAsRecordLocalId: 'localId', refName: 'feedbackTextarea' });
        this._feedbackTextareaRef = useRef('feedbackTextarea');
        onMounted(() => this._mounted());
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    _mounted() {
        this._feedbackTextareaRef.el.focus();
        if (this.activityMarkDonePopoverView.activityViewOwner.activity.feedbackBackup) {
            this._feedbackTextareaRef.el.value = this.activityMarkDonePopoverView.activityViewOwner.activity.feedbackBackup;
        }
    }

    /**
     * @returns {ActivityMarkDonePopoverView}
     */
    get activityMarkDonePopoverView() {
        return this.messaging && this.messaging.models['ActivityMarkDonePopoverView'].get(this.props.localId);
    }

}

Object.assign(ActivityMarkDonePopover, {
    props: {
        localId: String,
    },
    template: 'mail.ActivityMarkDonePopover',
});

registerMessagingComponent(ActivityMarkDonePopover);
