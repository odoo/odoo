import {patch} from "@web/core/utils/patch";
import {ListRenderer} from "@web/views/list/list_renderer";
import {onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import { uuid } from "@web/views/utils";


patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.bus = useService('bus_service');
        this.mergedView = `REALTIME_SYNC_${this.props.list.resModel}_${this.env.config.viewId}`;

        this.bus.subscribe(`NOTIFICATION_FROM_NEW_RECORD_TO_${this.mergedView}`, this.wsSyncView.bind(this));

        onWillUnmount(() => {
            if (this.bus && typeof this.bus.unsubscribe === "function") {
                this.bus.unsubscribe(`NOTIFICATION_FROM_NEW_RECORD_TO_${this.mergedView}`);
            }

        });

    },

    wsSyncView(args) {
        if (args.mergedView === `NOTIFICATION_FROM_NEW_RECORD_TO_${this.mergedView}`) {
            this.env.searchModel._notify()
        }
    },
});
