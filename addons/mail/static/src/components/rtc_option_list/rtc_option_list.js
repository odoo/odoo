/** @odoo-module **/

import { useComponentToModel } from '@mail/component_hooks/use_component_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { LegacyComponent } from "@web/legacy/legacy_component";

export class RtcOptionList extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component' });
    }

    /**
     * @returns {RtcOptionList}
     */
    get rtcOptionList() {
        return this.props.record;
    }

}

Object.assign(RtcOptionList, {
    props: { record: Object },
    template: 'mail.RtcOptionList',
});

registerMessagingComponent(RtcOptionList);
