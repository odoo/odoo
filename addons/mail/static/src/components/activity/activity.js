/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

import Popover from "web.Popover";
import { LegacyComponent } from "@web/legacy/legacy_component";

export class Activity extends LegacyComponent {

    /**
     * @override
     */
     setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
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
