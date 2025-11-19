import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { patch } from "@web/core/utils/patch";

patch(mailDataHelpers, {
    _process_request_for_internal_user(store, name, params) {
        super._process_request_for_internal_user(...arguments);
        if (name === "/im_livechat/session/data") {
            const DiscussChannel = this.env["discuss.channel"];
            const WebsiteVisitor = this.env["website.visitor"];
            const [channel] = DiscussChannel.browse(params.channel_id);
            const channelIds = DiscussChannel.search(
                [
                    ["channel_type", "=", "livechat"],
                    ["livechat_visitor_id", "=", channel.livechat_visitor_id],
                ],
                0,
                5
            );
            store._add_record_fields(WebsiteVisitor.browse(channel.livechat_visitor_id), {
                discuss_channel_ids: mailDataHelpers.Store.many(DiscussChannel.browse(channelIds)),
            });
        }
    },
});
