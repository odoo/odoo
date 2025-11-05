import { registry } from "@web/core/registry";
import { StoreLocator } from "./store_locator";
import { pick } from "@web/core/utils/objects";

const StoreLocatorEdit = (I) =>
    class extends I {
        start() {
            const locationList = JSON.parse(this.el.dataset.locationsList || "[]");
            if (locationList.length) {
                super.start();
            } else {
                this.renderAt("website.locationSelector.listIsEmpty");
            }
        }

        getConfigurationSnapshot() {
            // We keep only the map-related properties, because we dont want the
            // component to restart and flicker when irrelevant properties change
            // (e.g.: background settings).
            const keysToKeep = [
                "mapDetails",
                "mapHideOffscreenLocations",
                "mapSearchbar",
                "mapShowEmail",
                "mapShowPhone",
                "mapSidebar",
                "mapSidebarLocation",
                "mapZoom",
                "locationsList",
            ];
            const snapshot = JSON.parse(super.getConfigurationSnapshot() || "[]");
            const dataset = pick(snapshot.dataset, ...keysToKeep);
            return JSON.stringify(dataset);
        }
    };

registry.category("public.interactions.edit").add("website.store_locator_edit", {
    Interaction: StoreLocator,
    mixin: StoreLocatorEdit,
});
