import { DiscussSidebarChannel } from "@mail/discuss/core/public_web/discuss_app/sidebar/channel";
import { useDynamicInterval } from "@mail/utils/common/misc";

import { useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {DiscussSidebarChannel.prototype} */
const discussSidebarChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.helpState = useState({ text: "" });
        useDynamicInterval(
            (dt, selfMember) => {
                if (!dt || selfMember) {
                    return;
                }
                const diff = luxon.DateTime.now().diff(dt, ["days", "hours", "minutes", "seconds"]);
                if (diff.days >= 1) {
                    this.helpState.text = _t("%(days)sd", { days: diff.days });
                    return (diff.days + 1 - diff.as("days")) * 24 * 3600 * 1000;
                }
                if (diff.hours >= 1) {
                    this.helpState.text = _t("%(hours)sh", { hours: diff.hours });
                    return (diff.hours + 1 - diff.as("hours")) * 3600 * 1000;
                }
                this.helpState.text = diff.minutes
                    ? _t("%(minutes)sm", { minutes: diff.minutes })
                    : _t("< 1m");
                return (diff.minutes + 1 - diff.as("minutes")) * 60 * 1000;
            },
            () => [this.channel.livechat_looking_for_help_since_dt, this.channel.self_member_id]
        );
    },
};
patch(DiscussSidebarChannel.prototype, discussSidebarChannelPatch);
