/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from "@web/legacy/legacy_component";

export class CallLayoutMenu extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {CallLayoutMenu}
     */
    get callLayoutMenu() {
        return this.props.record;
    }

}

Object.assign(CallLayoutMenu, {
    props: { record: Object },
    template: 'mail.CallLayoutMenu',
});

registerMessagingComponent(CallLayoutMenu);
