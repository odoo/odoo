import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { isToday } from "@mail/utils/common/dates";
import { htmlToTextContentInline } from "@mail/utils/common/format";

import { Component, props, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class SubChannelPreview extends Component {
    static components = { AvatarStack };
    static template = "mail.SubChannelPreview";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = props({
            channel: t.instanceOf(this.store["discuss.channel"].Class),
            class: t.string().optional(),
            onClick: t.function([]).optional(),
        });
    }

    dateText(message) {
        if (isToday(message.datetime)) {
            return message.datetime?.toLocaleString(DateTime.TIME_SIMPLE);
        }
        return message.datetime?.toLocaleString(DateTime.DATE_MED);
    }

    bodyText(message) {
        return htmlToTextContentInline(message.body);
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

    get startedByText() {
        return _t("Started by %(name)s", { name: this.props.channel.create_uid.name });
    }
}
