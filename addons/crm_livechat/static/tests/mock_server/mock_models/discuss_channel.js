import { patch } from "@web/core/utils/patch";
import { DiscussChannel } from "@im_livechat/../tests/mock_server/mock_models/discuss_channel";

/** @type {import("mock_models").DiscussChannel} */
const discussChannelPatch = {
    _types_allowing_create_lead() {
        return super._types_allowing_create_lead(...arguments).concat(["livechat"]);
    },
};

patch(DiscussChannel.prototype, discussChannelPatch);
