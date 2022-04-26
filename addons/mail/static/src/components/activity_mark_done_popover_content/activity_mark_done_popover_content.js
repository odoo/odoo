/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from "@web/legacy/legacy_component";

const { onMounted, useRef } = owl;

export class ActivityMarkDonePopoverContent extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'ActivityMarkDonePopoverContentView' });
        useRefToModel({ fieldName: 'feedbackTextareaRef', modelName: 'ActivityMarkDonePopoverContentView', refName: 'feedbackTextarea' });
        this._feedbackTextareaRef = useRef('feedbackTextarea');
        onMounted(() => this._mounted());
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    _mounted() {
        this._feedbackTextareaRef.el.focus();
        if (this.activityMarkDonePopoverContentView.activityViewOwner.activity.feedbackBackup) {
            this._feedbackTextareaRef.el.value = this.activityMarkDonePopoverContentView.activityViewOwner.activity.feedbackBackup;
        }
    }

    /**
     * @returns {ActivityMarkDonePopoverContentView}
     */
    get activityMarkDonePopoverContentView() {
        return this.messaging && this.messaging.models['ActivityMarkDonePopoverContentView'].get(this.props.localId);
    }

}

Object.assign(ActivityMarkDonePopoverContent, {
    props: { localId: String },
    template: 'mail.ActivityMarkDonePopoverContent',
});

registerMessagingComponent(ActivityMarkDonePopoverContent);
