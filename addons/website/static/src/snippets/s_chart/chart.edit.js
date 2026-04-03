import { Chart } from "./chart";
import { registry } from "@web/core/registry";

const ChartEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.noAnimation = true;
        }

        start() {
            super.start();
            this.websiteEditService = this.services.website_edit;
            this.websiteEditService.callShared("builderOverlay", "refreshOverlays");
        }

        getConfigurationSnapshot() {
            let snapshot = super.getConfigurationSnapshot();
            snapshot = JSON.parse(snapshot || "{}");
            snapshot.bgColor = getComputedStyle(this.el).backgroundColor;
            snapshot = JSON.stringify(snapshot);
            return snapshot;
        }
    };

registry.category("public.interactions.edit").add("website.chart", {
    Interaction: Chart,
    mixin: ChartEdit,
});
