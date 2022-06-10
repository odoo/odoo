/** @odoo-module **/

import { useRefToModel } from '@mail/component_hooks/use_ref_to_model';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class CallDemoView extends Component {

    /**
     * @override
     */
    setup() {
        super.setup();
        useRefToModel({ fieldName: 'audioRef', refName: 'audio' });
        useRefToModel({ fieldName: 'videoRef', refName: 'video' });
    }

    /**
     * @returns {CallDemoView}
     */
    get callDemoView() {
        return this.props.record;
    }
}

Object.assign(CallDemoView, {
    props: { record: Object },
    template: 'mail.CallDemoView',
});

registerMessagingComponent(CallDemoView);
