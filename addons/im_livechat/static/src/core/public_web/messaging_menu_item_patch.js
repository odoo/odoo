import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import "@mail/discuss/core/public_web/messaging_menu_item_patch";
import { computedUntilStale } from "@mail/utils/common/signal";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {MessagingMenuItem} */
const messagingMenuItemPatch = {
    setup() {
        super.setup(...arguments);
        this.helpTime = computedUntilStale(
            () => {
                const dt = this.props.channel?.livechat_looking_for_help_since_dt;
                if (!dt) {
                    return { text: "", tooltip: "" };
                }
                const diff = luxon.DateTime.now().diff(dt, ["days", "hours", "minutes", "seconds"]);
                const withTooltip = ({ text, ms }) => ({
                    text,
                    tooltip: _t("Looking for help for: %(duration)s", { duration: text }),
                    ms,
                });
                if (diff.days >= 1) {
                    return withTooltip({
                        text: _t("%(days)sd", { days: diff.days }),
                        ms: (diff.days + 1 - diff.as("days")) * 24 * 3600 * 1000,
                    });
                }
                if (diff.hours >= 1) {
                    return withTooltip({
                        text: _t("%(hours)sh", { hours: diff.hours }),
                        ms: (diff.hours + 1 - diff.as("hours")) * 3600 * 1000,
                    });
                }
                return withTooltip({
                    text: diff.minutes ? _t("%(minutes)sm", { minutes: diff.minutes }) : _t("< 1m"),
                    ms: (diff.minutes + 1 - diff.as("minutes")) * 60 * 1000,
                });
            },
            ({ ms }) => ms
        );
    },
    get notificationItemProps() {
        const props = super.notificationItemProps;
        if (this.channel?.channel_type !== "livechat" || !props?.datetime) {
            return props;
        }
        return { ...props, dateText: this.livechatDateText(props.datetime) };
    },
    /** @param {import("luxon").DateTime} datetime */
    livechatDateText(datetime) {
        const startOfToday = this.store.startOfToday;
        if (datetime.hasSame(startOfToday, "day")) {
            const minutes = Math.floor(this.store.startOfMinute.diff(datetime, "minutes").minutes);
            if (minutes >= 60) {
                return _t("%(hours)sh", { hours: Math.floor(minutes / 60) });
            }
            return minutes > 0 ? _t("%(minutes)sm", { minutes }) : _t("< 1m");
        }
        if (datetime.hasSame(startOfToday.minus({ days: 1 }), "day")) {
            return _t("Yesterday");
        }
        if (startOfToday.diff(datetime.startOf("day"), "days").days < 7) {
            return datetime.toLocaleString({ weekday: "short" });
        }
        if (datetime.hasSame(startOfToday, "year")) {
            return datetime.toLocaleString({ month: "short", day: "numeric" });
        }
        return datetime.toLocaleString(luxon.DateTime.DATE_MED);
    },
};
patch(MessagingMenuItem.prototype, messagingMenuItemPatch);
