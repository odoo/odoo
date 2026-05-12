import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";

import { Component } from "@odoo/owl";
import { isBrowserSafari } from "@web/core/browser/feature_detection";

let nextId = 0;

/** @typedef {import("models").ChannelMember} ChannelMember */
/** @typedef {import("models").MailGuest} MailGuest */
/** @typedef {import("models").DiscussChannel} DiscussChannel */
/** @typedef {import("models").ResPartner} ResPartner */
/** @typedef {import("models").ResUsers} ResUsers */
/** @typedef {import("models").Thread} Thread */
/** @typedef {ChannelMember|DiscussChannel|MailGuest|ResPartner|ResUsers|Thread} DiscussAvatarRecord */

/**
 * @typedef {Object} Props
 * @property {string} [className=""]
 * @property {string} [iconExtraTransform]
 * @property {string} [imgRoundedClass]
 * @property {DiscussAvatarRecord} record
 * @property {number} [size=32]
 * @property {boolean} [typing=true]
 * @extends {Component<Props, Env>}
 */
export class DiscussAvatar extends Component {
    static template = "mail.DiscussAvatar";
    static props = [
        "className?",
        "iconExtraTransform?",
        "imgRoundedClass?",
        "record",
        "size?",
        "typing?",
    ];
    static defaultProps = { className: "", size: 32, typing: true };
    static components = { ImStatus, ThreadIcon };

    setup() {
        super.setup();
        this.isBrowserSafari = isBrowserSafari;
        this.uniqueId = `mail.DiscussAvatar.${nextId++}`;
    }

    /** @returns {DiscussChannel|undefined} */
    get channel() {
        const record = this.props.record;
        if (record.Model.getName() === "discuss.channel") {
            return record;
        }
        if (record.Model.getName() === "mail.thread") {
            return record.channel;
        }
        return undefined;
    }

    /** @returns {ChannelMember|undefined} */
    get channelMember() {
        const record = this.props.record;
        if (record.Model.getName() === "discuss.channel.member") {
            return record;
        }
        return undefined;
    }

    /** @returns {MailGuest|ResPartner|undefined} */
    get persona() {
        const record = this.props.record;
        if (record.Model.getName() === "res.users") {
            return record.partner_id;
        }
        if (["mail.guest", "res.partner"].includes(record.Model.getName())) {
            return record;
        }
        if (record.Model.getName() === "discuss.channel.member") {
            return record.persona;
        }
        return undefined;
    }

    /** @returns {MailThread|undefined} */
    get thread() {
        const record = this.props.record;
        if (record.Model.getName() === "mail.thread") {
            return record;
        }
        if (record.Model.getName() === "discuss.channel") {
            return record.thread;
        }
        return undefined;
    }

    get isTyping() {
        if (!this.props.typing) {
            return false;
        }
        if (this.channel) {
            return this.channel.hasOtherMembersTyping;
        }
        if (this.channelMember) {
            return this.channelMember.isTyping;
        }
        return false;
    }

    get showIcon() {
        if (this.channel) {
            return this.channel.showThreadIcon({ ignoreTyping: !this.props.typing });
        }
        return this.channelMember?.imStatusUI || this.persona?.imStatusUI;
    }

    /** @returns {ResUsers|undefined} */
    get user() {
        const record = this.props.record;
        if (record.Model.getName() === "res.users") {
            return record;
        }
        if (record.Model.getName() === "res.partner") {
            return record.main_user_id;
        }
        return undefined;
    }
}
