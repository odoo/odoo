import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { LivechatLookingForHelpReloadMixin } from "../livechat_looking_for_help_controller_mixin";

class DiscussChannelKanbanLookingForHelpController extends LivechatLookingForHelpReloadMixin(
    KanbanController
) {}

const discussChannelLookingForHelpKanbanView = {
    ...kanbanView,
    Controller: DiscussChannelKanbanLookingForHelpController,
};

registry
    .category("views")
    .add(
        "im_livechat.discuss_channel_looking_for_help_kanban",
        discussChannelLookingForHelpKanbanView
    );
