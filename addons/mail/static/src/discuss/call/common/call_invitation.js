/* @odoo-module */

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CallInvitation extends Component {
    static props = ["thread"];
    static template = "discuss.CallInvitation";

    setup() {
        this.threadService = useService("mail.thread");
        this.rtc = useService("discuss.rtc");
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
