import { AND, fields, Record } from "@mail/core/common/record";
import { rpc } from "@web/core/network/rpc";

export class MessageReactions extends Record {
    static id = AND("message", "content");

    /** @type {string} */
    content;
    /** @type {number} */
    count;
    guest_ids = fields.Many("mail.guest");
    message = fields.One("mail.message");
    partner_ids = fields.Many("res.partner");
    personas = fields.Many("Persona", {
        compute() {
            return [...this.partner_ids, ...this.guest_ids];
        },
    });
    /** @type {number} */
    sequence;

    async remove() {
        this.store.insert(
            await rpc(
                "/mail/message/reaction",
                {
                    action: "remove",
                    content: this.content,
                    message_id: this.message.id,
                    ...this.message.thread.rpcParams,
                },
                { silent: true }
            )
        );
    }
}

MessageReactions.register();
