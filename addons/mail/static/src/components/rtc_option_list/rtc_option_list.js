/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';
import { LegacyComponent } from "@web/legacy/legacy_component";

const { Component } = owl;

export class RtcOptionList extends LegacyComponent {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'RtcOptionList' });
    }

    /**
     * @returns {RtcOptionList}
     */
    get rtcOptionList() {
        return this.messaging && this.messaging.models['RtcOptionList'].get(this.props.localId);
    }

}

Object.assign(RtcOptionList, {
    props: { localId: String },
    template: 'mail.RtcOptionList',
});

registerMessagingComponent(RtcOptionList);
