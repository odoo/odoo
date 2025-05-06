import { DiscussChannelPivotModel } from "@im_livechat/views/discuss_channel_pivot/discuss_channel_pivot_model";

import { registry } from "@web/core/registry";
import { pivotView } from "@web/views/pivot/pivot_view";

const discussChannelPivotView = { ...pivotView, Model: DiscussChannelPivotModel };

registry.category("views").add("im_livechat.discuss_channel_pivot", discussChannelPivotView);
