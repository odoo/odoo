import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

let nextId = 0;

export class DiscussAvatar extends Component {
    static template = "mail.DiscussAvatar";
    static props = [
        "channel?",
        "member?",
        "persona?",
        "thread?",
        "size?",
        "typing?",
        "className?",
        "imgRoundedClass?",
    ];
    static defaultProps = { className: "", size: 32, typing: true };
    static components = { ImStatus, ThreadIcon };

    setup() {
        super.setup();
        this.uniqueId = `mail.DiscussAvatar.${nextId++}`;
        this.store = useService("mail.store");
    }

    get channel() {
        return this.props.channel ?? this.props.thread?.channel;
    }

    get thread() {
        return this.props.thread ?? this.props.channel?.thread;
    }

    get isTyping() {
        if (!this.props.typing) {
            return false;
        }
        if (this.channel) {
            return this.channel.hasOtherMembersTyping;
        }
        if (this.props.member) {
            return this.props.member.isTyping;
        }
        return false;
    }

    get showIcon() {
        if (this.channel) {
            return this.channel.showThreadIcon({ ignoreTyping: !this.props.typing });
        }
        if (!this.store.self_user || this.store.self_user.share === true) {
            return false;
        }
        if (this.props.member || this.props.persona) {
            return true;
        }
        return false;
    }
}
