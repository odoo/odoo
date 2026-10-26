import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";
import { Component, useEffect, useProps } from "@odoo/owl";

export class ThemeColorsLiveSync extends Component {
    static template = "website_livechat.ThemeColorsLiveSync";
    props = useProps(standardWidgetProps);

    setup() {
        const busService = useService("bus_service");
        this.orm = useService("orm");
        useEffect(() => {
            const resId = this.props.record.resId;
            if (!resId) {
                return;
            }
            const channel = `im_livechat.channel_${resId}/theme_sync`;
            busService.addChannel(channel);
            const unsubscribe = busService.subscribe(
                "im_livechat.channel/theme_colors_synced",
                (payload) => {
                    if (payload.id === resId) {
                        this.onThemeColorsSynced();
                    }
                }
            );
            return () => {
                unsubscribe();
                busService.deleteChannel(channel);
            };
        });
    }

    async onThemeColorsSynced() {
        const record = this.props.record;
        if (!record.dirty) {
            return record.load();
        }
        // Reloading would discard the pending edits, only bring the synced colors in.
        const [{ primary_color, secondary_color }] = await this.orm.read(
            "im_livechat.channel",
            [record.resId],
            ["primary_color", "secondary_color"]
        );
        await record.update({ primary_color, secondary_color });
    }
}

export const themeColorsLiveSync = {
    component: ThemeColorsLiveSync,
};
registry.category("view_widgets").add("theme_colors_live_sync", themeColorsLiveSync);
