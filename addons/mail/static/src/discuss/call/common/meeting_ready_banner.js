import { openChannelInvitationDialog } from "@mail/discuss/core/common/channel_invitation";

import { Component } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * Bottom-left "Your Meeting is Ready" banner shown while the current user is alone in the
 * call. It surfaces the permanent share link and a shortcut to invite people.
 *
 * @extends {Component<{}, Env>}
 */
export class MeetingReadyBanner extends Component {
    static template = "discuss.MeetingReadyBanner";

    setup() {
        super.setup();
        this.openChannelInvitationDialog = openChannelInvitationDialog;
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
    }

    /** @returns {import("models").DiscussChannel|undefined} channel hosting the call. */
    get channel() {
        return this.store.rtc.channel;
    }
}
