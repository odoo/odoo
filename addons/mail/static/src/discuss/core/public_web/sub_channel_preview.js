import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { propComputed } from "@mail/utils/common/hooks";

import { Component, computed, t, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { highlightText } from "@web/core/utils/html";

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
        this.channel = propComputed("channel", t.instanceOf(this.store["discuss.channel"]));
        this.class = propComputed("class", t.string().optional());
        this.searchTerm = propComputed("searchTerm", t.string().optional());
        this.highlightedThreadName = computed(() =>
            highlightText(this.searchTerm(), this.channel().displayName, HIGHLIGHT_CLASS)
        );
        this.onClick = useProps.static(
            "onClick",
            subChannelPreviewOnClickType(this.store).optional()
        );
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
