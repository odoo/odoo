/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcActivityNotice extends Component {

    /**
     * @returns {RtcActivityNoticeView}
     */
    get rtcActivityNoticeView() {
        return this.props.record;
    }

}

Object.assign(RtcActivityNotice, {
    props: { record: Object },
    template: 'mail.RtcActivityNotice',
});

registerMessagingComponent(RtcActivityNotice);
