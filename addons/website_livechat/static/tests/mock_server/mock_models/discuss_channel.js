import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields } from "@web/../tests/web_test_helpers";

export class DiscussChannel extends livechatModels.DiscussChannel {
    livechat_visitor_id = fields.Many2one({ relation: "website.visitor", string: "Visitor" }); // FIXME: somehow not fetched properly

    /**
     * @override
     * @type {typeof mailModels.DiscussChannel["prototype"]["_to_store"]}
     */
    _to_store(store) {
        /** @type {import("mock_models").WebsiteVisitor} */
        const WebsiteVisitor = this.env["website.visitor"];

        super._to_store(...arguments);
        for (const channel of this) {
            if (channel.channel_type === "livechat" && channel.livechat_visitor_id) {
                store._add_record_fields(this.browse(channel.id), {
                    livechat_visitor_id: mailDataHelpers.Store.one(
                        WebsiteVisitor.browse(channel.livechat_visitor_id)
                    ),
                });
            }
        }
    }
}
