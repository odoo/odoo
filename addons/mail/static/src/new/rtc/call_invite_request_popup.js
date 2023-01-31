/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class CallInviteRequestPopup extends Component {
    static props = ["thread"];
    static template = "mail.call_invite_request_popup";

    setup() {
        this.threadService = useService("mail.thread");
        this.rtc = useService("mail.rtc");
    }

    async onClickAccept(ev) {
        this.threadService.open(this.props.thread);
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        await this.rtc.toggleCall(this.props.thread);
    }

    onClickAvatar(ev) {
        this.threadService.open(this.props.thread);
    }

    onClickRefuse(ev) {
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        this.rtc.leaveCall(this.props.thread);
    }
}
