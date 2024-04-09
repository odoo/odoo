import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class CallInvitation extends Component {
    static props = ["thread"];
    static template = "discuss.CallInvitation";

    setup() {
        super.setup();
        this.rtc = useService("discuss.rtc");
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
