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
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'feedbackTextareaRef', refName: 'feedbackTextarea' });
        this._feedbackTextareaRef = useRef('feedbackTextarea');
        onMounted(() => this._mounted());
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    _mounted() {
        this._feedbackTextareaRef.el.focus();
        if (this.activityMarkDonePopoverContentView.activity.feedbackBackup) {
            this._feedbackTextareaRef.el.value = this.activityMarkDonePopoverContentView.activity.feedbackBackup;
        }
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
