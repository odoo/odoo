import { ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";

import { Component, props, t } from "@odoo/owl";

import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

let nextId = 0;

export class DiscussAvatar extends Component {
    static template = "mail.DiscussAvatar";
    static components = { ImStatus, ThreadIcon };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            className: t.string().optional(""),
            iconExtraTransform: t.string().optional(),
            imgRoundedClass: t.string().optional(),
            record: t.or([
                t.instanceOf(this.store["discuss.channel.member"].Class),
                t.instanceOf(this.store["discuss.channel"].Class),
                t.instanceOf(this.store["mail.guest"].Class),
                t.instanceOf(this.store["res.partner"].Class),
                t.instanceOf(this.store["res.users"].Class),
                t.instanceOf(this.store["mail.thread"].Class),
            ]),
            size: t.number().optional(32),
            typing: t.boolean().optional(true),
        });
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
            return this.channelMember.isTypingUi;
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
