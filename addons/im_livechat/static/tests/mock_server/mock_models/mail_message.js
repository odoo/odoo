import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { makeKwArgs } from "@web/../tests/web_test_helpers";

export class MailMessage extends mailModels.MailMessage {
    _author_to_store(ids, store) {
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        const messages_w_author_livechat = MailMessage.browse(ids).filter((message) => {
            if (!message.author_id || message.model !== "discuss.channel" || !message.res_id) {
                return false;
            }
            const channel = DiscussChannel.browse(message.res_id);
            return channel.channel_type === "livechat";
        });
        super._author_to_store(
            ids.filter(
                (id) => !messages_w_author_livechat.map((message) => message.id).includes(id)
            ),
            store
        );
        for (const message of messages_w_author_livechat) {
            store.add(this.browse(message.id), {
                author: mailDataHelpers.Store.one(
                    ResPartner.browse(message.author_id),
                    makeKwArgs({
                        fields: ["is_company", "user_livechat_username", "user", "write_date"],
                    })
                ),
            });
        }
    }
}
