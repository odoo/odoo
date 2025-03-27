import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { convertBrToLineBreak } from "@mail/utils/common/format";


const messagePatch = {
    showInsertButton: true,
    async copyMessageText() {
        let notification = _t("Message Copied!");
        let type = "info";
        try {
            const messageBody = convertBrToLineBreak(this.body)
            await browser.navigator.clipboard.writeText(messageBody);
        } catch {
            notification = _t("Message Copy Failed (Permission denied?)!");
            type = "danger";
        }
        this.store.env.services.notification.add(notification, { type });
    },
};

patch(Message.prototype, messagePatch);
