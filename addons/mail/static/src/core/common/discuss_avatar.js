import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";

import { Component } from "@odoo/owl";

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
            if (this.channel.channel_type === "chat" && !this.channel.correspondent?.im_status) {
                return false;
            }
            return this.channel.showThreadIcon({ ignoreTyping: !this.props.typing });
        }
        if (this.props.member?.persona.im_status || this.props.persona?.im_status) {
            return true;
        }
        return false;
    }
}
