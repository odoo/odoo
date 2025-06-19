import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";

threadActionsRegistry.add("info", {
    component: LivechatChannelInfoList,
    condition(component) {
        return component.thread?.channel_type === "livechat";
    },
    panelOuterClass: "o-livechat-ChannelInfoList bg-inherit",
    icon: "fa fa-fw fa-info",
    iconLarge: "fa fa-fw fa-lg fa-info",
    name: _t("Information"),
    nameActive: _t("Close Information"),
    sequence: 40,
    sequenceGroup: 6,
    toggle: true,
});
