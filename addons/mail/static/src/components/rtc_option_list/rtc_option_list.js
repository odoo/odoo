/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';
import { useComponentToModel } from '@mail/component_hooks/use_component_to_model/use_component_to_model';

const { Component } = owl;

export class RtcOptionList extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useComponentToModel({ fieldName: 'component', modelName: 'mail.rtc_option_list', propNameAsRecordLocalId: 'localId' });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.rtc_option_list}
     */
    get rtcOptionList() {
        return this.messaging && this.messaging.models['mail.rtc_option_list'].get(this.props.localId);
    }

}

Object.assign(RtcOptionList, {
    props: {
        localId: String,
    },
    template: 'mail.RtcOptionList',
});

registerMessagingComponent(RtcOptionList);
