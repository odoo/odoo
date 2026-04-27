import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { url } from "@web/core/utils/urls";

patch(Message.prototype, {
    async copyLink() {
        if (this.thread?.model === "knowledge.article.thread") {
            let notification = _t("Message Link Copied!");
            let type = "info";
            try {
                await browser.navigator.clipboard.writeText(
                    url(`/knowledge/article/${this.thread.articleId}`)
                );
            } catch {
                notification = _t("Message Link Copy Failed (Permission denied?)!");
                type = "danger";
            }
            this.store.env.services.notification.add(notification, { type });
        } else {
            return super.copyLink(...arguments);
        }
    },
});
