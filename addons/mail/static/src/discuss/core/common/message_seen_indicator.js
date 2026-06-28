import { useRef } from "@web/owl2/utils";
import { Component, props, t, useListener } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useBackButton, useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";

class MessageSeenIndicatorDialog extends Component {
    static components = { Dialog };
    static template = "mail.MessageSeenIndicatorDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            close: t.function([]).optional(),
            message: t.instanceOf(this.store["mail.message"].Class),
        });
        this.contentRef = useRef("content");
        useListener(
            browser,
            "click",
            (ev) => {
                if (!this.contentRef?.el.contains(ev.target)) {
                    this.props.close();
                }
            },
            true
        );
        useBackButton(() => this.props.close());
    }
}

export class MessageSeenIndicator extends Component {
    static template = "mail.MessageSeenIndicator";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            className: t.string().optional(),
            message: t.instanceOf(this.store["mail.message"].Class),
        });
        this.dialog = useService("dialog");
    }

    get summary() {
        if (this.props.message.hasEveryoneSeen) {
            if (
                this.props.message.channel_id.correspondent &&
                this.props.message.channel_id.channel_member_ids.length === 2
            ) {
                return _t("Seen by %(user)s", {
                    user: this.props.message.channel_id.correspondent.name,
                });
            }
            return _t("Seen by everyone");
        }
        const seenMembers = this.props.message.channelMemberHaveSeen;
        const [user1, user2, user3] = seenMembers.map((member) => member.name);
        switch (seenMembers.length) {
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
        this.dialog.add(MessageSeenIndicatorDialog, { message: this.props.message });
    }
}
