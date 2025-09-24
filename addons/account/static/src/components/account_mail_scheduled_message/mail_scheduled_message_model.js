import { patch } from "@web/core/utils/patch";
import { RPCError } from "@web/core/network/rpc";
import { ScheduledMessage } from "@mail/chatter/web/scheduled_message_model";

// account specific modifications
patch(ScheduledMessage.prototype, {
    async cancel() {
        await this.store.env.services.orm.call("mail.scheduled.message", "account_log_cancellation", [
            this.id,
        ]);
        await super.cancel();
    },
    // patching this method, cause parent method catches all the errors
    async send() {
        try {
            await this.store.env.services.orm.call("mail.scheduled.message", "post_message", [
                this.id,
            ]);
        } catch(error) {
            if (error instanceof RPCError) {
                throw error;  // re-raise errors only from server-side
            }
            return;
        }
    }
})
