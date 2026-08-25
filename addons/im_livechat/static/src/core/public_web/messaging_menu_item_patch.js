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
                const dt = this.channel?.livechat_looking_for_help_since_dt;
                if (!dt) {
                    return { text: "" };
                }
                const diff = luxon.DateTime.now().diff(dt, ["days", "hours", "minutes", "seconds"]);
                if (diff.days >= 1) {
                    return {
                        text: _t("%(days)sd", { days: diff.days }),
                        ms: (diff.days + 1 - diff.as("days")) * 24 * 3600 * 1000,
                    };
                }
                if (diff.hours >= 1) {
                    return {
                        text: _t("%(hours)sh", { hours: diff.hours }),
                        ms: (diff.hours + 1 - diff.as("hours")) * 3600 * 1000,
                    };
                }
                return {
                    text: diff.minutes ? _t("%(minutes)sm", { minutes: diff.minutes }) : _t("< 1m"),
                    ms: (diff.minutes + 1 - diff.as("minutes")) * 60 * 1000,
                };
            },
            ({ ms }) => ms
        );
    },
};
patch(MessagingMenuItem.prototype, messagingMenuItemPatch);
