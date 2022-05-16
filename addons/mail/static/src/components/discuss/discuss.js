/** @odoo-module **/

import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class Discuss extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        useUpdateToModel({ methodName: 'onComponentUpdate' });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {DiscussView}
     */
    get discussView() {
        return this.props.record;
    }
}

Object.assign(Discuss, {
    props: { record: Object },
    template: 'mail.Discuss',
});

registerMessagingComponent(Discuss);
