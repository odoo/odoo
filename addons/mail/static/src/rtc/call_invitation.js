/* @odoo-module */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CallInvitation extends Component {
    static props = ["thread"];
    static template = "mail.CallInvitation";

    setup() {
        this.threadService = useService("mail.thread");
        this.rtc = useService("mail.rtc");
    }

    async onClickAccept(ev) {
        this.props.thread.open();
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        await this.rtc.toggleCall(this.props.thread);
    }

    onClickAvatar(ev) {
        this.props.thread.open();
    }

    onClickRefuse(ev) {
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        this.rtc.leaveCall(this.props.thread);
    }
}
