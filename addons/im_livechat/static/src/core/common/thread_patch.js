import { Thread } from "@mail/core/common/thread";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(Thread.prototype, {
    get showVisitorDisconnected() {
        return (
            this.store.self.notEq(this.channel?.livechatVisitorMember?.persona) &&
            !this.channel?.livechat_end_dt &&
            this.channel?.livechatVisitorMember?.persona?.offline_since
        );
    },
    get disconnectedText() {
        const offlineSince = this.props.thread.channel?.livechatVisitorMember.persona.offline_since;
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
