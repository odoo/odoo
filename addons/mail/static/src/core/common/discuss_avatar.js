import { getImStatusData, ImStatus } from "@mail/core/common/im_status";
import { ThreadIcon } from "@mail/core/common/thread_icon";

import { Component, onMounted, onPatched, Portal, signal, t, useEffect, useProps } from "@odoo/owl";

import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

let nextId = 0;

/** Avatar size the icons are designed for: icons shrink on smaller avatars. */
const ICON_REFERENCE_SIZE = 32;

export class DiscussAvatar extends Component {
    static template = "mail.DiscussAvatar";
    static components = { ImStatus, Portal, ThreadIcon };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            className: t.string().optional(""),
            imgRoundedClass: t.string().optional(),
            record: t.or([
                t.instanceOf(this.store["discuss.channel.member"]),
                t.instanceOf(this.store["discuss.channel"]),
                t.instanceOf(this.store["mail.guest"]),
                t.instanceOf(this.store["res.partner"]),
                t.instanceOf(this.store["res.users"]),
                t.instanceOf(this.store["mail.thread"]),
            ]),
            size: t.number().optional(32),
            typing: t.boolean().optional(true),
        });
        this.isBrowserSafari = isBrowserSafari;
        this.uniqueId = `mail.DiscussAvatar.${nextId++}`;
        /** Space between the icon and the cut out of the avatar, in icon pixels. */
        this.iconMaskGap = 1.5;
        this.rootRef = signal.ref();
        this.iconRef = signal.ref();
        this.glyphMaskRef = signal.ref();
        this.rectMaskRef = signal.ref();
        onMounted(() => this.updateIconMask());
        onPatched(() => this.updateIconMask());
        useEffect(() => {
            const iconEl = this.iconRef();
            if (!iconEl) {
                return;
            }
            const resizeObserver = new ResizeObserver(() => this.updateIconMask());
            resizeObserver.observe(iconEl);
            return () => resizeObserver.disconnect();
        });
    }

    get iconScale() {
        return Math.min(1, this.props.size / ICON_REFERENCE_SIZE);
    }

    /**
     * Fits the icon mask to the icon as rendered, so that it works whatever the icon (IM status,
     * typing indicator, thread icon, ...) and its size.
     */
    updateIconMask() {
        const rootEl = this.rootRef();
        const iconEl = this.iconRef();
        const glyphMaskEl = this.glyphMaskRef();
        const rectMaskEl = this.rectMaskRef();
        if (!rootEl || !iconEl || (!glyphMaskEl && !rectMaskEl)) {
            return;
        }
        const rootRect = rootEl.getBoundingClientRect();
        const iconRect = iconEl.getBoundingClientRect();
        // client rects include transforms of ancestors, SVG user units are CSS pixels of the root
        const ratio = rootRect.width / rootEl.offsetWidth || 1;
        const x = (iconRect.left - rootRect.left) / ratio;
        const y = (iconRect.top - rootRect.top) / ratio;
        const width = iconRect.width / ratio;
        const height = iconRect.height / ratio;
        const scale = this.iconScale;
        if (glyphMaskEl) {
            // glyph starts at its x and is vertically centered on its y (dominant-baseline)
            glyphMaskEl.setAttribute(
                "transform",
                `translate(${x}, ${y + height / 2}) scale(${scale})`
            );
            return;
        }
        const gap = this.iconMaskGap * scale;
        rectMaskEl.setAttribute("x", x - gap);
        rectMaskEl.setAttribute("y", y - gap);
        rectMaskEl.setAttribute("width", width + 2 * gap);
        rectMaskEl.setAttribute("height", height + 2 * gap);
        rectMaskEl.setAttribute("rx", Math.min(width, height) / 2 + gap);
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

    get showIconMask() {
        return this.showIcon;
    }

    get imStatusData() {
        if (this.isTyping || (this.thread && !this.channel?.showImStatus)) {
            return undefined;
        }
        const member = this.channelMember || this.channel?.correspondent;
        const persona = member?.persona || this.persona;
        if (!persona) {
            return undefined;
        }
        return getImStatusData({ member, persona, user: this.user || persona.main_user_id });
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
