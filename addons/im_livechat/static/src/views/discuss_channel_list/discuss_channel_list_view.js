import { DiscussChannelRelationalModel } from "@im_livechat/views/discuss_channel_relational_model";
import { LivechatViewControllerMixin } from "@im_livechat/views/livechat_view_controller_mixin";

import { registry } from "@web/core/registry";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

class DiscussChannelListController extends LivechatViewControllerMixin(ListController) {}

const discussChannelListView = {
    ...listView,
    Controller: DiscussChannelListController,
    Model: DiscussChannelRelationalModel,
};

registry.category("views").add("im_livechat.discuss_channel_list", discussChannelListView);
