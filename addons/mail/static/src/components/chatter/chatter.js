/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from '@web/legacy/legacy_component';

export class Chatter extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
        useRefToModel({ fieldName: 'scrollPanelRef', refName: 'scrollPanel' });
    }

    /**
     * @returns {Chatter}
     */
    get chatter() {
        return this.props.record;
    }

}

Object.assign(Chatter, {
    props: { record: Object },
    template: 'mail.Chatter',
});

registerMessagingComponent(Chatter);
