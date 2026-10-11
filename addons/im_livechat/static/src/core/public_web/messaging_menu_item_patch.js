import { MessagingMenuItem } from "@mail/core/public_web/messaging_menu/messaging_menu_item";
import "@mail/discuss/core/public_web/messaging_menu_item_patch";
import { computedUntilStale } from "@mail/utils/common/signal";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { PANEL_CONTAINER_TYPE } from "@mail/core/common/action";

/** @type {MessagingMenuItem} */
const messagingMenuItemPatch = {
    setup() {
        super.setup(...arguments);
        this.helpTime = computedUntilStale(
            () => {
                const dt = this.channel?.livechat_looking_for_help_since_dt;
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
    /**
     * The status selection is a list that fills the dropdown on its own.
     *
     * @type {MessagingMenuItem["getPanelContainer"]}
     */
    getPanelContainer(params) {
        if (this.channel && params.action.id === "livechat-status") {
            return { type: PANEL_CONTAINER_TYPE.DROPDOWN, menuClass: "p-0" };
        }
        return super.getPanelContainer(params);
    },
};
patch(MessagingMenuItem.prototype, messagingMenuItemPatch);
