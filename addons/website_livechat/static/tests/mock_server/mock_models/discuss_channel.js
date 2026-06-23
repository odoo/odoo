import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { fields } from "@web/../tests/web_test_helpers";

export class DiscussChannel extends livechatModels.DiscussChannel {
    livechat_visitor_id = fields.Many2one({ relation: "website.visitor", string: "Visitor" }); // FIXME: somehow not fetched properly

    _store_channel_fields(res) {
        super._store_channel_fields(res);
        res.one(
            "livechat_visitor_id",
            (visitorRes) => {
                visitorRes.from_method("_store_visitor_fields");
                visitorRes.from_method("_store_visitor_history_fields");
            },
            {
                predicate: (channel) =>
                    channel.channel_type === "livechat" && channel.livechat_visitor_id,
            }
        );
    }
}
