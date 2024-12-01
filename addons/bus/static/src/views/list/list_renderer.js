import {patch} from "@web/core/utils/patch";
import {ListRenderer} from "@web/views/list/list_renderer";
import {onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        this.bus = useService('bus_service');
        this.mergedView = `realtime_sync_${this.props.list.resModel}_${this.env.config.viewId}`;

        this.bus.addChannel(this.mergedView);
        this.bus.subscribe('NOTIFICATION_FROM_NEW_RECORD', this.wsSyncView.bind(this));

        onWillUnmount(() => {
            if (this.bus && typeof this.bus.deleteChannel === "function") {
                this.bus.deleteChannel(this.mergedView);
            }
            if (this.bus && typeof this.bus.unsubscribe === "function") {
                this.bus.unsubscribe('NOTIFICATION_FROM_NEW_RECORD');
            }

        });

    },

    wsSyncView(args) {
        if (args.mergedView === this.mergedView) {
            this.env.searchModel._notify()
        }
    },
});
