import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { isToday } from "@mail/utils/common/dates";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, props, t } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

/** @param {import("models").Store} store */
export const subChannelPreviewOnClickType = (store) =>
    t.function([
        t.instanceOf(MouseEvent),
        t.object({ channelAtRender: t.instanceOf(store["discuss.channel"].Class) }),
    ]);

export class SubChannelPreview extends Component {
    static components = { AvatarStack };
    static template = "mail.SubChannelPreview";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.channel = propComputed("channel", t.instanceOf(this.store["discuss.channel"].Class));
        this.class = propComputed("class", t.string().optional());
        this.onClick = props.static("onClick", subChannelPreviewOnClickType(this.store).optional());
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

    get messageCountText() {
        if (this.channel().message_count === 1) {
            return _t("1 Message");
        }
        return _t("%(count)s Messages", { count: this.channel().message_count });
    }

    get startedByText() {
        return _t("Started by %(name)s", { name: this.channel().create_uid.name });
    }
}
