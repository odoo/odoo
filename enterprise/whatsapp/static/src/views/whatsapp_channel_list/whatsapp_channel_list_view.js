import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

import { WhatsappChannelListController } from "./whatsapp_channel_list_view_controller";

const whatsappChannelListView = {
    ...listView,
    Controller: WhatsappChannelListController,
};

registry.category("views").add("whatsapp.discuss_channel_list", whatsappChannelListView);
