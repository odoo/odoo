/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useUpdateToModel } from '@mail/component_hooks/use_update_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class Discuss extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        useComponentToModel({ fieldName: 'component' });
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
