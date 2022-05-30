/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from "@web/legacy/legacy_component";

export class CallOptionMenu extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {CallOptionMenu}
     */
    get callOptionMenu() {
        return this.props.record;
    }

}

Object.assign(CallOptionMenu, {
    props: { record: Object },
    template: 'mail.CallOptionMenu',
});

registerMessagingComponent(CallOptionMenu);
