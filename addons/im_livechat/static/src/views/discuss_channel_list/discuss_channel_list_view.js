import { ListController } from "@web/views/list/list_controller";
import { LivechatViewControllerMixin } from "../livechat_view_controller_mixin";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

class DiscussChannelListController extends LivechatViewControllerMixin(ListController) {}

const discussChannelListView = {
    ...listView,
    Controller: DiscussChannelListController,
};

registry.category("views").add("im_livechat.discuss_channel_list", discussChannelListView);
