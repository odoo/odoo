import { selfOrderIndex } from "@pos_self_order/app/self_order_index";
import { EventPage } from "@pos_self_order_event/app/pages/event_page/event_page";
import { patch } from "@web/core/utils/patch";

patch(selfOrderIndex, {
    components: {
        ...selfOrderIndex.components,
        EventPage,
    },
});
