import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";
import { stateToUrl } from "@web/core/browser/router";

import { patch } from "@web/core/utils/patch";

patch(LivechatChannelInfoList.prototype, {
    setup() {
        super.setup();
        this.stateToUrl = stateToUrl;
    },
});
