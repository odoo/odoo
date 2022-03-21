/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from "@web/legacy/legacy_component";

export class RtcLayoutMenu extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'RtcLayoutMenu' });
    }

    /**
     * @returns {RtcLayoutMenu}
     */
    get layoutMenu() {
        return this.messaging && this.messaging.models['RtcLayoutMenu'].get(this.props.localId);
    }

}

Object.assign(RtcLayoutMenu, {
    props: { localId: String },
    template: 'mail.RtcLayoutMenu',
});

registerMessagingComponent(RtcLayoutMenu);
