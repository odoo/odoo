import { propComputed } from "@mail/utils/common/hooks";

import { Component, types } from "@odoo/owl";

/** Tells how long ago the invitation of a channel member who has not joined yet was last sent. */
export class InvitationSentDate extends Component {
    static template = "discuss.InvitationSentDate";

    setup() {
        super.setup();
        this.datetime = propComputed("datetime", types.instanceOf(luxon.DateTime));
    }

    get relativeTime() {
        return this.datetime().toRelative({ style: "narrow" });
    }
}
