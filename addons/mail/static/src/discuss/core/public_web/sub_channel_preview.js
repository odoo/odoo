import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { htmlToTextContentInline } from "@mail/utils/common/format";

import { Component, t, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/** @param {import("models").Store} store */
export const subChannelPreviewOnClickType = (store) =>
    t.function([
        t.instanceOf(MouseEvent),
        t.object({ channelAtRender: t.instanceOf(store["discuss.channel"]) }),
    ]);

export class SubChannelPreview extends Component {
    static components = { AvatarStack };
    static template = "mail.SubChannelPreview";

    setup() {
        super.setup(...arguments);
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.signal(t.instanceOf(this.store["discuss.channel"])),
            class: t.signal(t.string()).optional(),
            onClick: subChannelPreviewOnClickType(this.store).optional().static(),
        });
    }

    bodyText(message) {
        return htmlToTextContentInline(message.body);
    }

    get messageCountText() {
        if (this.props.channel().message_count === 1) {
            return _t("1 Message");
        }
        return _t("%(count)s Messages", { count: this.props.channel().message_count });
    }

    get startedByText() {
        return _t("Started by %(name)s", { name: this.props.channel().create_uid.name });
    }
}
