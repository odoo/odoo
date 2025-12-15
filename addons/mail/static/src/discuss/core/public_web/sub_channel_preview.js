import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { isToday } from "@mail/utils/common/dates";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class SubChannelPreview extends Component {
    static components = { AvatarStack };
    static template = "mail.SubChannelPreview";
    static props = ["channel", "class?", "onClick?"];

    dateText(message) {
        if (isToday(message.datetime)) {
            return message.datetime?.toLocaleString(DateTime.TIME_SIMPLE);
        }
        return message.datetime?.toLocaleString(DateTime.DATE_MED);
    }

    onClick() {
        this.props.onClick?.();
    }

    get messageCountText() {
        if (this.props.channel.message_count === 1) {
            return _t("1 Message");
        }
        return _t("%(count)s Messages", { count: this.props.channel.message_count });
    }
}
