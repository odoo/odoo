/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from "@web/legacy/legacy_component";

const { Component, onMounted, useRef } = owl;

export class ActivityMarkDonePopover extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'ActivityMarkDonePopoverView' });
        useRefToModel({ fieldName: 'feedbackTextareaRef', modelName: 'ActivityMarkDonePopoverView', refName: 'feedbackTextarea' });
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
    props: { localId: String },
    template: 'mail.ActivityMarkDonePopover',
});

registerMessagingComponent(ActivityMarkDonePopover);
