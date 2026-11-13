import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";
import { AvatarStack } from "@mail/discuss/core/common/avatar_stack";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { propComputed, propStatic, usePropsPlus } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, computed, t } from "@odoo/owl";

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
        this.ancestors = useAncestors();
        this.store = useService("mail.store");
        this.props = usePropsPlus({
            channel: propComputed(t.instanceOf(this.store["discuss.channel"])),
            class: propComputed(t.string().optional()),
            onClick: propStatic(subChannelPreviewOnClickType(this.store).optional()),
            searchTerm: propComputed(t.string().optional("")),
        });
        this.threadName = computed(() =>
            this.props
                .searchTerm()
                .split(" ")
                .reduce(
                    (name, word) => highlightText(word, name, HIGHLIGHT_CLASS),
                    this.props.channel().displayName
                )
        );
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
