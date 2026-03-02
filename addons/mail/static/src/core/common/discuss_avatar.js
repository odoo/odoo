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
        "rtcSession?",
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

    get member() {
        return this.props.member ?? this.props.rtcSession?.channel_member_id;
    }

    get thread() {
        return this.props.thread ?? this.props.channel?.thread;
    }

    get isTyping() {
        if (!this.props.typing || this.props.rtcSession) {
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

    get showTopLeftIcon() {
        if (this.props.rtcSession) {
            return this.props.rtcSession.raisingHand;
        }
        return false;
    }

    get showTopRightIcon() {
        if (this.props.rtcSession) {
            return true; // managed in SCSS for :hover
        }
        return false;
    }

    get showBottomRightIcon() {
        if (this.channel) {
            return this.channel.showThreadIcon({ ignoreTyping: !this.props.typing });
        }
        if (this.props.member || this.props.persona) {
            return true;
        }
        if (this.props.rtcSession) {
            return this.props.rtcSession.is_deaf || this.props.rtcSession.is_muted;
        }
        return false;
    }
}
