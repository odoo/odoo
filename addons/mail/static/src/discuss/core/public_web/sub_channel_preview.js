import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { isToday } from "@mail/utils/common/dates";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class SubChannelPreview extends Component {
    static components = { AvatarStack };
    static template = "mail.SubChannelPreview";
    static props = ["class?", "onClick?", "channel"];

    dateText(message) {
        if (isToday(message.datetime)) {
            return message.datetime?.toLocaleString(DateTime.TIME_SIMPLE);
        }
        return message.datetime?.toLocaleString(DateTime.DATE_MED);
    }

    get channel() {
        return this.props.channel;
    }

    onClick() {
        this.props.onClick?.();
    }

    get messageCountText() {
        if (this.channel.message_count === 1) {
            return _t("1 Message");
        }
        return _t("%(count)s Messages", { count: this.channel.message_count });
    }
}
