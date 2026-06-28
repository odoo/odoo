import { Component, props, t } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class Typing extends Component {
    static template = "discuss.Typing";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            channel: t.instanceOf(this.store["discuss.channel"].Class).optional(),
            displayText: t.boolean().optional(true),
            member: t.instanceOf(this.store["discuss.channel.member"].Class).optional(),
            size: t.string().optional("small"),
        });
        this.isBrowserSafari = isBrowserSafari;
    }

    /** @returns {string} */
    get text() {
        const typingMemberNames = this.props.member
            ? [this.props.member.name]
            : this.props.channel.otherTypingMembers.map(({ name }) => name);
        if (typingMemberNames.length === 1) {
            return _t("%s is typing...", typingMemberNames[0]);
        }
        if (typingMemberNames.length === 2) {
            return _t("%(user1)s and %(user2)s are typing...", {
                user1: typingMemberNames[0],
                user2: typingMemberNames[1],
            });
        }
        return _t("%(user1)s, %(user2)s and more are typing...", {
            user1: typingMemberNames[0],
            user2: typingMemberNames[1],
        });
    }

    get showTypingIcon() {
        return true;
    }
}
