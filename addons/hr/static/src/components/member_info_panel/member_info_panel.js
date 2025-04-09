import { ChannelMemberInfo } from "@mail/discuss/core/common/member_info_panel";

import { patch } from "@web/core/utils/patch";

export const patchChannelMemberInfo = {
    get correspondentInfoKeys() {
        return [...super.correspondentInfoKeys, "designation", "department", "workplace"];
    },
};

patch(ChannelMemberInfo.prototype, patchChannelMemberInfo);
