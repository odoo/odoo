import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { LivechatViewControllerMixin } from "../livechat_view_controller_mixin";

class DiscussChannelKanbanController extends LivechatViewControllerMixin(KanbanController) {}

const discussChannelKanbanView = {
    ...kanbanView,
    Controller: DiscussChannelKanbanController,
};

registry.category("views").add("im_livechat.discuss_channel_kanban", discussChannelKanbanView);
