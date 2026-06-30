import { Component, useExternalListener, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";

class MessageSeenIndicatorDialog extends Component {
    static components = { Dialog };
    static template = "mail.MessageSeenIndicatorDialog";
    static props = ["message", "close?"];

    setup() {
        super.setup();
        this.contentRef = useRef("content");
        useExternalListener(
            browser,
            "click",
            (ev) => {
                if (!this.contentRef?.el.contains(ev.target)) {
                    this.props.close();
                }
            },
            true
        );
    }
}

/**
 * @typedef {Object} Props
 * @property {import("models").Message} message
 * @property {import("models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class MessageSeenIndicator extends Component {
    static template = "mail.MessageSeenIndicator";
    static props = ["message", "thread", "className?"];

    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    get summary() {
        if (this.props.message.hasEveryoneSeen) {
            if (
                this.props.thread.correspondent &&
                this.props.thread.channel_member_ids.length === 2
            ) {
                return _t("Seen by %(user)s", { user: this.props.thread.correspondent.name });
            }
            return _t("Seen by everyone");
        }
        const seenMembers = this.props.message.channelMemberHaveSeen;
        const [user1, user2, user3] = seenMembers.map((member) => member.name);
        switch (seenMembers.length) {
            case 0:
                return _t("Sent");
            case 1:
                return _t("Seen by %(user)s", { user: user1 });
            case 2:
                return _t("Seen by %(user1)s and %(user2)s", { user1, user2 });
            case 3:
                return _t("Seen by %(user1)s, %(user2)s and %(user3)s", { user1, user2, user3 });
            case 4:
                return _t("Seen by %(user1)s, %(user2)s, %(user3)s and 1 other", {
                    user1,
                    user2,
                    user3,
                });
            default:
                return _t("Seen by %(user1)s, %(user2)s, %(user3)s and %(count)s others", {
                    user1,
                    user2,
                    user3,
                    count: seenMembers.length - 3,
                });
        }
    }

    openDialog() {
        if (this.props.message.channelMemberHaveSeen.length === 0) {
            return;
        }
        this.dialog.add(MessageSeenIndicatorDialog, { message: this.props.message });
    }
}
