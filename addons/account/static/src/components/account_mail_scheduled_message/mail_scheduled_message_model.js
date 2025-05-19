import { ScheduledMessage } from "@mail/chatter/web/scheduled_message_model";
import { patch } from "@web/core/utils/patch";

patch(ScheduledMessage.prototype, {
    async cancel() {
        await this.store.env.services.orm.call("mail.scheduled.message", "account_log_cancellation", [
            this.id,
        ]);
        await super.cancel();
    }
})
