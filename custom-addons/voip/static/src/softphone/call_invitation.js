/* @odoo-module */

import { Component } from "@odoo/owl";

import { Correspondence } from "@voip/core/correspondence_model";

import { useService } from "@web/core/utils/hooks";

export class CallInvitation extends Component {
    static props = {
        correspondence: { type: Correspondence },
        extraClass: { type: String, optional: true },
    };
    static template = "voip.CallInvitation";

    setup() {
        this.userAgent = useService("voip.user_agent");
    }

    /** @returns {string} */
    get partnerName() {
        return this.props.correspondence.partner?.name ?? "";
    }

    /** @param {MouseEvent} ev */
    onClickAccept(ev) {
        this.userAgent.acceptIncomingCall();
    }

    /** @param {MouseEvent} ev */
    onClickReject(ev) {
        this.userAgent.rejectIncomingCall();
    }
}
