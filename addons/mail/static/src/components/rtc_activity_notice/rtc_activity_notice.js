/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcActivityNotice extends Component {
    get rtcActivityNoticeView() {
        return this.messaging && this.messaging.models['RtcActivityNotice'].get(this.props.localId);
    }
}

Object.assign(RtcActivityNotice, {
    props: { localId: String },
    template: 'mail.RtcActivityNotice',
});

registerMessagingComponent(RtcActivityNotice);
