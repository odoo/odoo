/* @odoo-module */

import { DiscussChannelListController } from "@im_livechat/views/discuss_channel_list/discuss_channel_list_view_controller";

import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

const discussChannelListView = {
    ...listView,
    Controller: DiscussChannelListController,
};

registry.category("views").add("im_livechat.discuss_channel_list", discussChannelListView);
