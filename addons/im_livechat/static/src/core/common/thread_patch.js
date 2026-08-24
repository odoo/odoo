import { Thread } from "@mail/core/common/thread";
import { useEffect } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.IM_STATUS_DELAY = 1500;
        Object.assign(this.state, { isVisitorOffline: false }); // starting online avoids flickering
        useEffect(
            () => {
                if (!this.props.thread.livechatVisitorMember?.persona?.im_status) {
                    return;
                }
                clearTimeout(this.imStatusTimeoutId);
                if (this.props.thread.livechatVisitorMember.persona.im_status.includes("offline")) {
                    this.imStatusTimeoutId = setTimeout(
                        () => (this.state.isVisitorOffline = true),
                        this.IM_STATUS_DELAY
                    );
                } else {
                    this.state.isVisitorOffline = false;
                }
                return () => clearTimeout(this.imStatusTimeoutId);
            },
            () => [this.props.thread.livechatVisitorMember?.persona?.im_status]
        );
        useEffect(
            (loadNewer, mountedAndLoaded) => {
                const el = this.scrollableRef.el;
                if (
                    el &&
                    !loadNewer &&
                    mountedAndLoaded &&
                    this.props.thread.selfMember &&
                    !this.props.thread.markedAsUnread &&
                    this.props.thread.channel_type === "livechat" &&
                    Math.abs(el.scrollTop + el.clientHeight - el.scrollHeight) <= 1
                ) {
                    this.props.thread.markAsRead({ sync: true });
                }
            },
            () => [this.props.thread.loadNewer, this.state.mountedAndLoaded, this.state.scrollTop]
        );
    },
    get showVisitorDisconnected() {
        return (
            this.store.self.notEq(this.props.thread.livechatVisitorMember?.persona) &&
            this.props.thread.livechat_active &&
            this.props.thread.livechatVisitorMember &&
            this.state.isVisitorOffline
        );
    },
    get disconnectedText() {
        const offlineSince = this.props.thread.livechatVisitorMember.persona.offline_since;
        if (!offlineSince) {
            return _t("Visitor is disconnected");
        }
        const userLocale = { locale: user.lang };
        if (offlineSince.hasSame(DateTime.now(), "day")) {
            return _t("Visitor is disconnected since %(time)s", {
                time: offlineSince.toLocaleString(DateTime.TIME_SIMPLE, userLocale),
            });
        }
        if (offlineSince.hasSame(DateTime.now().minus({ day: 1 }), "day")) {
            return _t("Visitor is disconnected since yesterday at %(time)s", {
                time: offlineSince.toLocaleString(DateTime.TIME_SIMPLE, userLocale),
            });
        }
        return _t("Visitor is disconnected");
    },
});
