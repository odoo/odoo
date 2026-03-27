import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    onKeydown(ev) {
        super.onKeydown(ev);
        if (
            ev.key === "Tab" &&
            this.thread?.channel_type === "livechat" &&
            !this.props.composer.composerText
        ) {
            const threadChanged = this.store.goToOldestUnreadLivechatThread();
            if (threadChanged) {
                // prevent chat window from switching to the next thread: as
                // we want to go to the oldest unread thread, not the next
                // one.
                ev.stopPropagation();
            }
        }
    },
    get placeholder() {
        if (this.displayNextLivechatHint() && this.props.composer.isFocused) {
            return _t("Tab to next livechat");
        }
        return super.placeholder;
    },
    displayNextLivechatHint() {
        return (
            this.thread?.channel_type === "livechat" &&
            this.store.discuss.livechats.some(
                (thread) => thread.notEq(this.thread) && thread.isUnread
            )
        );
    },
});
