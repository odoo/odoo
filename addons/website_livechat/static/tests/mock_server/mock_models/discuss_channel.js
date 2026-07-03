import { livechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { fields } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";

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

    _store_livechat_extra_fields(res) {
        super._store_livechat_extra_fields(res);
        /** @type {import("mock_models").DiscussChannel} */
        const DiscussChannel = this.env["discuss.channel"];
        res.one("livechat_visitor_id", (visitorRes) =>
            visitorRes.many("discuss_channel_ids", "_store_channel_fields", {
                value: (visitor) =>
                    DiscussChannel.browse(
                        DiscussChannel.search(
                            [
                                ["channel_type", "=", "livechat"],
                                ["livechat_visitor_id", "=", visitor.id],
                                [
                                    "create_date",
                                    ">=",
                                    serializeDateTime(luxon.DateTime.now().minus({ days: 7 })),
                                ],
                            ],
                            0,
                            5
                        )
                    ),
            })
        );
    }
}
