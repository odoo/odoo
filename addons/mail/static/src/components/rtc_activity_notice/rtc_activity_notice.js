/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcActivityNotice extends Component {

    /**
     * @returns {RtcActivityNoticeView}
     */
    get rtcActivityNoticeView() {
        return this.messaging && this.messaging.models['RtcActivityNoticeView'].get(this.props.localId);
    }

}

Object.assign(RtcActivityNotice, {
    props: { localId: String },
    template: 'mail.RtcActivityNotice',
});

registerMessagingComponent(RtcActivityNotice);
