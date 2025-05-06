import { DiscussChannelRelationalModel } from "@im_livechat/views/discuss_channel_relational_model";
import { LivechatViewControllerMixin } from "@im_livechat/views/livechat_view_controller_mixin";

import { registry } from "@web/core/registry";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";

class DiscussChannelKanbanController extends LivechatViewControllerMixin(KanbanController) {}

const discussChannelKanbanView = {
    ...kanbanView,
    Controller: DiscussChannelKanbanController,
    Model: DiscussChannelRelationalModel,
};

registry.category("views").add("im_livechat.discuss_channel_kanban", discussChannelKanbanView);
