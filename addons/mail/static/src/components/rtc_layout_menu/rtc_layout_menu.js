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
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {RtcLayoutMenu}
     */
    get layoutMenu() {
        return this.props.record;
    }

}

Object.assign(RtcLayoutMenu, {
    props: { record: Object },
    template: 'mail.RtcLayoutMenu',
});

registerMessagingComponent(RtcLayoutMenu);
