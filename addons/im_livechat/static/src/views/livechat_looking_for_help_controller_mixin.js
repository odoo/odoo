import { LivechatViewControllerMixin } from "@im_livechat/views/livechat_view_controller_mixin";

import { onWillDestroy } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

const RELOAD_DEBOUNCE_DELAY = 300;

export const LivechatLookingForHelpReloadMixin = (ViewController) =>
    class extends LivechatViewControllerMixin(ViewController) {
        setup() {
            super.setup(...arguments);
            const busService = useService("bus_service");
            this.reloadDebounced = useDebounced(() => this.model.load(), RELOAD_DEBOUNCE_DELAY);
            this.lookingForHelpOnUpdate = this.lookingForHelpOnUpdate.bind(this);
            busService.addChannel("im_livechat.looking_for_help");
            busService.subscribe(
                "im_livechat.looking_for_help/update",
                this.lookingForHelpOnUpdate
            );
            onWillDestroy(() => {
                busService.unsubscribe(
                    "im_livechat.looking_for_help/update",
                    this.lookingForHelpOnUpdate
                );
                busService.deleteChannel("im_livechat.looking_for_help");
            });
        }

        lookingForHelpOnUpdate({ added_channel_ids, removed_channel_ids }) {
            const recordIdByResId = {};
            this.model.root.records.forEach((rec) => (recordIdByResId[rec.resId] = rec.id));
            if (added_channel_ids.some((resId) => !recordIdByResId[resId])) {
                // Filter/Groups/Search are handled server side, it's easier to reload the data
                // rather than trying to guess where/if the record should be inserted.
                this.reloadDebounced();
                return;
            }
            const recordIdsToRemove = removed_channel_ids
                .map((resId) => recordIdByResId[resId])
                .filter(Boolean);
            if (recordIdsToRemove.length) {
                this.model.root._removeRecords(recordIdsToRemove);
            }
        }
    };
