import { Component, markup, t, useProps } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { createDocumentFragmentFromContent } from "@web/core/utils/html";

export class Typing extends Component {
    static template = "discuss.Typing";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]).optional(),
            displayText: t.boolean().optional(true),
            member: t.instanceOf(this.store["discuss.channel.member"]).optional(),
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
            return _t("%s is typing...", markup`<b>${typingMemberNames[0]}</b>`);
        }
        if (typingMemberNames.length === 2) {
            return _t("%(user1)s and %(user2)s are typing...", {
                user1: markup`<b>${typingMemberNames[0]}</b>`,
                user2: markup`<b>${typingMemberNames[1]}</b>`,
            });
        }
        return _t("%(user1)s, %(user2)s and more are typing...", {
            user1: markup`<b>${typingMemberNames[0]}</b>`,
            user2: markup`<b>${typingMemberNames[1]}</b>`,
        });
    }

    get showTypingIcon() {
        return true;
    }

    /** @returns {string} */
    get textTitle() {
        return createDocumentFragmentFromContent(this.text).body.textContent;
    }
}
