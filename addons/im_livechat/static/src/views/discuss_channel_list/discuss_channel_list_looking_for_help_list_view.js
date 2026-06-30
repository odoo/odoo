import { LivechatLookingForHelpReloadMixin } from "@im_livechat/views/livechat_looking_for_help_controller_mixin";

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class DiscussChannelLookingForHelpListController extends LivechatLookingForHelpReloadMixin(
    ListController
) {}

const discussChannelLookingForHelpListView = {
    ...listView,
    Controller: DiscussChannelLookingForHelpListController,
};

registry
    .category("views")
    .add("im_livechat.discuss_channel_looking_for_help_list", discussChannelLookingForHelpListView);
