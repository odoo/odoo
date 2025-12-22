import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

import { useService } from "@web/core/utils/hooks";

export class SnailmailError extends Component {
    static components = { Dialog };
    static props = ["close", "failureType", "messageId"];
    static template = "snailmail.SnailmailError";

    setup() {
        this.orm = useService("orm");
    }

    async fetchSnailmailCreditsUrl() {
        return await this.orm.call("iap.account", "get_credits_url", ["snailmail"]);
    }

    async fetchSnailmailCreditsUrlTrial() {
        return await this.orm.call("iap.account", "get_credits_url", ["snailmail", "", 0, true]);
    }

    async onClickResendLetter() {
        await this.orm.call("mail.message", "send_letter", [[this.props.messageId]]);
        this.props.close();
    }

    async onClickCancelLetter() {
        await this.orm.call("mail.message", "cancel_letter", [[this.props.messageId]]);
        this.props.close();
    }

    get snailmailCreditsUrl() {
        return this.fetchSnailmailCreditsUrl();
    }

    get snailmailCreditsUrlTrial() {
        return this.fetchSnailmailCreditsUrlTrial();
    }
}
