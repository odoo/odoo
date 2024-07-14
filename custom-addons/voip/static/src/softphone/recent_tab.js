/* @odoo-module */

import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class RecentTab extends Component {
    static props = { extraClass: { type: String, optional: true }, recentCalls: { type: Array } };
    static defaultProps = { extraClass: "" };
    static template = "voip.RecentTab";

    setup() {
        this.voip = useState(useService("voip"));
        this.orm = useService("orm");
        this.callService = useService("voip.call");
        onMounted(() => this.voip.fetchRecentCalls());
    }

    /**
     * @param {MouseEvent} ev
     * @param {import("@voip/core/call_model").Call} call
     */
    onClickPhoneCall(ev, call) {
        this.voip.softphone.selectCorrespondence({ call });
    }
}
